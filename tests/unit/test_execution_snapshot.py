from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from creator_studio.domain.shot import (
    AssetRef,
    CandidateSpec,
    ControlPass,
    EnvironmentSpec,
    ExecutionSnapshot,
    GenerationParams,
    IdempotencyAction,
    ModelArtifactRef,
    decide_idempotency,
    decide_revision_policy,
)


def snapshot(*, extras: bool = False) -> ExecutionSnapshot:
    model = ModelArtifactRef(content_hash="a" * 64)
    return ExecutionSnapshot(
        shot_id="shot-1", shot_revision=1,
        source=AssetRef("source", "b" * 64), depth=AssetRef("depth", "c" * 64),
        pose=AssetRef("pose", "d" * 64) if extras else None,
        control_passes=[ControlPass("depth", 0.8)],
        generation=GenerationParams("夜の街", "", 42, 20, 7, 0.6, "euler", "normal"),
        candidates=CandidateSpec(2, "repeat_latent_batch"),
        environment=EnvironmentSpec(
            "template", "e" * 64, model, model, model,
            depth_patch=model if extras else None, pose_patch=model if extras else None,
        ),
    )


@pytest.mark.parametrize("extras", [False, True])
def test_construction_and_roundtrip(extras: bool) -> None:
    value = snapshot(extras=extras)
    assert (value.pose is not None) == extras
    assert (value.environment.depth_patch is not None) == extras
    assert (value.environment.pose_patch is not None) == extras
    assert value.schema_version == value.to_dict()["schema_version"] == 1
    for data in (value.to_dict(), json.loads(value.canonical_json())):
        restored = ExecutionSnapshot.from_dict(data)
        assert restored == value
        assert restored.to_dict() == value.to_dict()
        assert restored.snapshot_hash == value.snapshot_hash


def test_frozen() -> None:
    value = snapshot()
    with pytest.raises(FrozenInstanceError):
        value.shot_revision = 2
    with pytest.raises(FrozenInstanceError):
        value.source.sha256 = "f" * 64
    assert isinstance(value.control_passes, tuple)
    with pytest.raises(AttributeError):
        value.control_passes.append(ControlPass("pose", 1))
    controls = [ControlPass("depth", 1)]
    copied = replace(value, control_passes=controls)
    controls.clear()
    assert len(copied.control_passes) == 1
    assert replace(value, control_passes=()).control_passes == ()


@pytest.mark.parametrize("kwargs", [
    {}, {"content_hash": "anima.safetensors"},
    {"immutable_revision": "model.safetensors"}, {"immutable_revision": "model.CKPT"},
    {"immutable_revision": "model.pt"}, {"immutable_revision": "model.pth"},
    {"immutable_revision": "model.bin"}, {"immutable_revision": "path/revision"},
    {"immutable_revision": "path\\revision"}, {"immutable_revision": " "},
    {"content_hash": "a" * 64, "immutable_revision": "bad.bin"},
])
def test_invalid_model_identity(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        ModelArtifactRef(**kwargs)


def test_revision_model_identity() -> None:
    assert ModelArtifactRef(immutable_revision="rev-2026-11-13-abc123").content_hash is None


@pytest.mark.parametrize("digest", ["abc", "A" * 64, "image.png", "g" * 64, "a" * 65])
def test_invalid_hashes(digest: str) -> None:
    with pytest.raises(ValueError):
        AssetRef("asset", digest)
    with pytest.raises(ValueError):
        replace(snapshot().environment, template_hash=digest)
    with pytest.raises(ValueError):
        ModelArtifactRef(content_hash=digest)


def test_hash_determinism() -> None:
    first, second = snapshot(), snapshot()
    assert first.snapshot_hash == second.snapshot_hash

    def reverse_keys(value):
        if isinstance(value, dict):
            return {key: reverse_keys(value[key]) for key in reversed(value)}
        if isinstance(value, list):
            return [reverse_keys(item) for item in value]
        return value

    assert ExecutionSnapshot.from_dict(reverse_keys(first.to_dict())).snapshot_hash == (
        first.snapshot_hash
    )
    assert first.canonical_json() == json.dumps(
        first.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert "夜の街" in first.canonical_json()


@pytest.mark.parametrize("field", [
    "seed", "positive", "depth", "template_hash", "candidate_count", "strength", "shot_revision",
])
def test_hash_sensitivity(field: str) -> None:
    value = snapshot()
    changes = {
        "seed": {"generation": replace(value.generation, seed=43)},
        "positive": {"generation": replace(value.generation, positive="different")},
        "depth": {"depth": replace(value.depth, sha256="f" * 64)},
        "template_hash": {"environment": replace(value.environment, template_hash="f" * 64)},
        "candidate_count": {"candidates": replace(value.candidates, candidate_count=3)},
        "strength": {"control_passes": (ControlPass("depth", 0.9),)},
        "shot_revision": {"shot_revision": 2},
    }
    assert replace(value, **changes[field]).snapshot_hash != value.snapshot_hash


def test_control_order_changes_hash() -> None:
    value = replace(snapshot(), control_passes=(ControlPass("depth", 1), ControlPass("pose", 1)))
    assert replace(value, control_passes=value.control_passes[::-1]).snapshot_hash != (
        value.snapshot_hash
    )


FORBIDDEN = ["prompt_id", "progress", "error", "error_message", "status", "external_job_ref"]


def test_no_execution_state() -> None:
    def check(value):
        if isinstance(value, dict):
            assert not set(value).intersection(FORBIDDEN)
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(snapshot(extras=True).to_dict())


@pytest.mark.parametrize("key", FORBIDDEN + ["unknown"])
@pytest.mark.parametrize("location", ["root", "generation", "checkpoint", "control"])
def test_unknown_keys_rejected(key: str, location: str) -> None:
    data = snapshot().to_dict()
    target = {
        "root": data, "generation": data["generation"],
        "checkpoint": data["environment"]["checkpoint"], "control": data["control_passes"][0],
    }[location]
    target[key] = "unexpected"
    with pytest.raises(ValueError, match="unknown"):
        ExecutionSnapshot.from_dict(data)


@pytest.mark.parametrize("job_id,existing", [(None, None), ("job-1", None), (None, snapshot())])
def test_idempotency_create(job_id, existing) -> None:
    decision = decide_idempotency(job_id, existing, snapshot())
    assert decision.action == IdempotencyAction.CREATE_NEW
    assert decision.http_status is None
    assert decision.existing_job_id is None


def test_idempotency_reuse_and_conflict() -> None:
    value = snapshot()
    reuse = decide_idempotency("job-1", value, snapshot())
    assert reuse.action == IdempotencyAction.REUSE_EXISTING
    assert reuse.existing_job_id == "job-1"
    assert reuse.http_status is None
    conflict = decide_idempotency("job-1", value, replace(value, shot_revision=2))
    assert conflict.action == IdempotencyAction.CONFLICT
    assert conflict.http_status == 409
    assert conflict.existing_job_id == "job-1"


@pytest.mark.parametrize("replay,current,allowed,stale,latest", [
    (False, 1, True, False, True), (False, 2, False, True, False),
    (True, 2, True, True, False), (True, 1, True, False, True),
])
def test_revision_policy(replay, current, allowed, stale, latest) -> None:
    decision = decide_revision_policy(snapshot(), current, is_replay=replay)
    assert (decision.allowed, decision.is_stale, decision.treat_as_latest) == (
        allowed, stale, latest,
    )
    assert decision.reason
    if not allowed:
        assert "Enqueue-time revision mismatch" in decision.reason
        assert "refused" in decision.reason


def test_schema_incompatibility() -> None:
    data = snapshot().to_dict()
    data["schema_version"] = 999
    with pytest.raises(ValueError, match="schema_version"):
        ExecutionSnapshot.from_dict(data)
    with pytest.raises(ValueError, match="schema_version"):
        replace(snapshot(), schema_version=True)


@pytest.mark.parametrize("field,value", [
    ("seed", True), ("steps", True), ("steps", 0), ("steps", 1.5),
    ("cfg", True), ("cfg", 0), ("cfg", float("inf")), ("denoise", -0.1),
    ("denoise", 1.1), ("denoise", float("nan")), ("sampler", ""), ("scheduler", " "),
    ("positive", None), ("negative", 1),
])
def test_invalid_generation(field, value) -> None:
    with pytest.raises(ValueError):
        replace(snapshot().generation, **{field: value})


@pytest.mark.parametrize("count", [True, 0, 9, 1.5])
def test_invalid_candidate_count(count) -> None:
    with pytest.raises(ValueError):
        CandidateSpec(count, "single")


@pytest.mark.parametrize("strength", [True, "1", float("nan"), float("inf")])
def test_invalid_control_strength(strength) -> None:
    with pytest.raises(ValueError):
        ControlPass("depth", strength)


@pytest.mark.parametrize("field,value", [
    ("shot_id", " "), ("shot_revision", 0), ("shot_revision", True),
    ("source", {}), ("depth", None), ("pose", {}), ("generation", {}),
    ("candidates", {}), ("environment", {}), ("control_passes", ["depth"]),
    ("control_passes", None),
])
def test_invalid_snapshot(field, value) -> None:
    with pytest.raises(ValueError):
        replace(snapshot(), **{field: value})


def test_malformed_dicts() -> None:
    for data in ({}, [], {"source": []}):
        with pytest.raises(ValueError):
            ExecutionSnapshot.from_dict(data)
