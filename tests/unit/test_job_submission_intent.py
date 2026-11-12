from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from creator_studio.application.jobs.manage_jobs import EnqueueJobCommand, FencingError
from creator_studio.application.jobs.submission import (
    JobSubmissionService,
    ReconcileOutcome,
    SubmissionAlreadyRecordedError,
    SubmissionAttemptConflictError,
    SubmissionIntentMissingError,
)
from creator_studio.domain.ids import JobId
from creator_studio.domain.job import Job, JobKind, SubmissionIntent, make_correlation_key
from creator_studio.infrastructure.db.repositories.mappers import (
    apply_job_to_row,
    job_from_row,
    job_to_row,
)


class FakeSubmissionClient:
    def __init__(self):
        self.queue: dict[str, str] = {}
        self.history: dict[str, str] = {}
        self.submit_calls = 0
        self.lookup_calls = 0
        self.on_submit: Callable[[str], None] | None = None
        self.fail_submit = False

    def submit(self, *, correlation_key: str) -> str:
        self.submit_calls += 1
        if self.on_submit:
            self.on_submit(correlation_key)
        if self.fail_submit:
            raise RuntimeError("submit failed")
        prompt_id = f"prompt-{self.submit_calls}"
        self.queue[prompt_id] = correlation_key
        return prompt_id

    def lookup_prompt_id(self, *, correlation_key: str) -> str | None:
        self.lookup_calls += 1
        for collection in (self.queue, self.history):
            for prompt_id, key in collection.items():
                if key == correlation_key:
                    return prompt_id
        return None

    def move_to_history(self, prompt_id: str) -> None:
        self.history[prompt_id] = self.queue.pop(prompt_id)

    def drop(self, prompt_id: str) -> None:
        self.queue.pop(prompt_id, None)
        self.history.pop(prompt_id, None)


def claimed(container):
    container.enqueue_job().execute(EnqueueJobCommand(kind=JobKind.STUB))
    job = container.claim_runner().claim()
    assert job is not None
    return job


@pytest.mark.parametrize("failure", [False, True])
def test_committed_intent_gate_and_submit_order(container, failure):
    job = claimed(container)
    service = JobSubmissionService(container.uow())
    with pytest.raises(SubmissionIntentMissingError):
        service.record_prompt_id(job.id, "ungated")
    fake = FakeSubmissionClient()

    def check_persisted(key):
        persisted = container.get_job().execute(job.id)
        assert persisted.submission_correlation_key == key
        assert persisted.external_job_ref is None

    fake.on_submit = check_persisted
    fake.fail_submit = failure
    if failure:
        with pytest.raises(RuntimeError, match="submit failed"):
            service.submit(job.id, fake, expected_attempts=1)
    else:
        result = service.submit(job.id, fake, expected_attempts=1)
        assert result.external_job_ref == "prompt-1"
    persisted = container.get_job().execute(job.id)
    assert persisted.submission_correlation_key == f"sw-job:{job.id}:attempt:1"
    assert persisted.external_job_ref == (None if failure else "prompt-1")
    assert persisted.status == job.status
    assert fake.submit_calls == 1


@pytest.mark.parametrize("history", [False, True])
def test_restart_reconnects_queue_or_history(container, history):
    job = claimed(container)
    with container.uow() as uow:
        domain_job = uow.jobs.get(JobId(job.id))
        domain_job.progress = {"existing": 7}
        uow.jobs.save(domain_job)
        uow.commit()
    intent = JobSubmissionService(container.uow()).begin_submission(job.id)
    fake = FakeSubmissionClient()
    prompt_id = fake.submit(correlation_key=intent.submission_correlation_key)
    if history:
        fake.move_to_history(prompt_id)
    service = JobSubmissionService(container.uow())
    result = service.reconcile(job.id, fake, expected_attempts=1)
    assert result.outcome == ReconcileOutcome.RECONNECTED
    assert result.job.external_job_ref == prompt_id
    assert result.job.status == job.status
    assert result.job.progress == {"existing": 7, "submission_reconciled": True}
    assert container.get_job().execute(job.id) == result.job
    assert fake.lookup_calls == 1
    assert fake.submit_calls == 1
    assert service.reconcile(job.id, fake).outcome == ReconcileOutcome.ALREADY_RECORDED
    assert fake.lookup_calls == 1
    with pytest.raises(SubmissionAlreadyRecordedError):
        service.begin_submission(job.id)


def test_unknown_submission_blocks_and_can_be_reconciled_again(container):
    job = claimed(container)
    service = JobSubmissionService(container.uow())
    intent = service.begin_submission(job.id)
    fake = FakeSubmissionClient()
    prompt_id = fake.submit(correlation_key=intent.submission_correlation_key)
    fake.drop(prompt_id)
    result = service.reconcile(job.id, fake)
    assert result.outcome == ReconcileOutcome.BLOCKED
    assert result.job.status == "blocked"
    assert result.job.lease_owner is None
    assert result.job.leased_until is None
    assert intent.submission_correlation_key in result.job.error_message
    assert "automatic resubmit is disabled" in result.job.error_message
    assert container.claim_runner().claim() is None
    assert service.reconcile(job.id, fake).outcome == ReconcileOutcome.BLOCKED
    fake.history[prompt_id] = intent.submission_correlation_key
    recovered = service.reconcile(job.id, fake)
    assert recovered.outcome == ReconcileOutcome.RECONNECTED
    assert recovered.job.status == "blocked"
    assert fake.submit_calls == 1
    assert fake.lookup_calls == 3


def test_not_submitted_is_read_only(container):
    job = claimed(container)
    fake = FakeSubmissionClient()
    result = JobSubmissionService(container.uow()).reconcile(job.id, fake)
    assert result.outcome == ReconcileOutcome.NOT_SUBMITTED
    assert result.job == job
    assert fake.lookup_calls == fake.submit_calls == 0


@pytest.mark.parametrize("operation", ["begin", "record", "reconcile"])
@pytest.mark.parametrize("has_intent", [False, True])
def test_stale_attempt_cannot_mutate(container, operation, has_intent):
    job = claimed(container)
    service = JobSubmissionService(container.uow())
    if has_intent:
        service.begin_submission(job.id)
    before = container.get_job().execute(job.id)
    fake = FakeSubmissionClient()
    with pytest.raises(FencingError):
        if operation == "begin":
            service.begin_submission(job.id, expected_attempts=0)
        elif operation == "record":
            service.record_prompt_id(job.id, "stale", expected_attempts=0)
        else:
            service.reconcile(job.id, fake, expected_attempts=0)
    assert container.get_job().execute(job.id) == before
    assert fake.lookup_calls == fake.submit_calls == 0


def test_idempotent_intent_and_repository_round_trip(container):
    job = claimed(container)
    service = JobSubmissionService(container.uow())
    first = service.begin_submission(job.id, expected_attempts=1)
    assert service.begin_submission(job.id, expected_attempts=1) == first
    key = f"sw-job:{job.id}:attempt:1"
    assert first.submission_correlation_key == key
    assert first.submission_provider == "comfyui"
    assert first.submission_attempt == 1
    assert first.submission_intended_at
    with container.uow() as uow:
        persisted = uow.jobs.get_by_submission_correlation_key(key)
        assert persisted.id == job.id
        assert persisted.submission_intent == SubmissionIntent.from_json(
            persisted.submission_intent.to_json()
        )
        assert persisted.submission_intended_at.isoformat() == first.submission_intended_at
        assert uow.jobs.get_by_submission_correlation_key("absent") is None
        persisted.attempts = 2
        uow.jobs.save(persisted)
        uow.commit()
    with pytest.raises(SubmissionAttemptConflictError, match="reconcile"):
        service.begin_submission(job.id, expected_attempts=2)


@pytest.mark.parametrize("attempt", [True, False, 0, -1, 1.5, "1", None])
def test_invalid_correlation_attempt(attempt):
    with pytest.raises(ValueError):
        make_correlation_key("job", attempt)


@pytest.mark.parametrize("job_id", ["", " ", None, 1])
def test_invalid_correlation_job_id(job_id):
    with pytest.raises(ValueError):
        make_correlation_key(job_id, 1)


def test_intent_validation_serialization_and_freeze():
    intent = SubmissionIntent("job", 1, "sw-job:job:attempt:1", snapshot_hash="a" * 64)
    assert SubmissionIntent.from_dict(intent.to_dict()) == intent
    assert SubmissionIntent.from_json(intent.to_json()) == intent
    assert intent.to_json() == SubmissionIntent.from_json(intent.to_json()).to_json()
    with pytest.raises(ValueError, match="unknown"):
        SubmissionIntent.from_dict({**intent.to_dict(), "extra": 1})
    for changes in (
        {"correlation_key": "wrong"}, {"provider": ""}, {"snapshot_hash": "A" * 64},
        {"snapshot_hash": "short"}, {"intended_at": "invalid"},
    ):
        with pytest.raises(ValueError):
            replace(intent, **changes)
    job = Job.create(JobKind.STUB)
    job.submission_intent = intent
    job.submission_intent = replace(intent, provider="another")
    assert job.submission_intent is intent
    for other in (None, replace(intent, attempt=2, correlation_key="sw-job:job:attempt:2")):
        with pytest.raises(ValueError, match="frozen"):
            job.submission_intent = other
    row = job_to_row(job)
    assert job_from_row(row).submission_intent == intent
    replacement = Job.create(JobKind.STUB)
    with pytest.raises(ValueError, match="frozen"):
        apply_job_to_row(replacement, row)


@pytest.mark.parametrize("corruption", ["json", "shape", "unknown", "key", "missing"])
def test_corrupt_intent_rejected(corruption):
    job = Job.create(JobKind.STUB)
    job.submission_intent = SubmissionIntent("job", 1, "sw-job:job:attempt:1")
    row = job_to_row(job)
    if corruption == "json":
        row.submission_intent_json = "{"
    elif corruption == "shape":
        row.submission_intent_json = "{}"
    elif corruption == "unknown":
        row.submission_intent_json = '{"extra":true}'
    elif corruption == "key":
        row.submission_correlation_key = "wrong"
    else:
        row.submission_intent_json = None
    with pytest.raises(ValueError, match="corrupt"):
        job_from_row(row)


@pytest.mark.parametrize("operation", ["begin", "record", "reconcile"])
def test_missing_job(container, operation):
    service = JobSubmissionService(container.uow())
    with pytest.raises(ValueError, match="job not found"):
        if operation == "begin":
            service.begin_submission("absent")
        elif operation == "record":
            service.record_prompt_id("absent", "prompt")
        else:
            service.reconcile("absent", FakeSubmissionClient())


@pytest.mark.parametrize("prompt_id", ["", " ", None])
def test_empty_prompt_rejected(container, prompt_id):
    job = claimed(container)
    service = JobSubmissionService(container.uow())
    before = service.begin_submission(job.id)
    with pytest.raises(ValueError, match="non-empty"):
        service.record_prompt_id(job.id, prompt_id)
    assert container.get_job().execute(job.id) == before
