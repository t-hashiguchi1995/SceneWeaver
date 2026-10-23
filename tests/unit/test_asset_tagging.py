from __future__ import annotations

from creator_studio.adapters.vision import StubImageTagger
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.assets.tag_asset import TagAsset, tagging_idempotency_key
from creator_studio.application.jobs.manage_jobs import ClaimAndRunStubJob
from creator_studio.application.visual_library import VisualLibraryQuery
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.job import JobKind, JobStatus
from creator_studio.infrastructure.container import Container


def test_stub_tagger_is_deterministic() -> None:
    tagger = StubImageTagger()
    a = tagger.tag(b"same-bytes")
    b = tagger.tag(b"same-bytes")
    assert a.tags == b.tags
    assert a.source_model == "stub"
    assert any(t.tag == "stub_auto" for t in a.tags)


def test_store_asset_enqueues_tag_job_without_blocking(container: Container) -> None:
    dto = container.store_asset().execute(
        StoreBytesCommand(
            data=b"tag-me-please",
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename="shot.png",
        )
    )
    with container.uow() as uow:
        job = uow.jobs.get_by_idempotency_key(tagging_idempotency_key(dto.id))
        assert job is not None
        assert job.kind == JobKind.TAG_ASSET
        assert job.status == JobStatus.QUEUED
        assert job.payload.get("asset_id") == dto.id


def test_tag_asset_persists_and_is_idempotent(container: Container) -> None:
    dto = container.store_asset().execute(
        StoreBytesCommand(
            data=b"persist-tags",
            kind=AssetKind.REFERENCE,
            mime="image/png",
            relative_dir="refs",
            filename="ref.png",
        )
    )
    service = TagAsset(container.uow(), container.asset_store, container.image_tagger())
    first = service.execute(dto.id)
    second = service.execute(dto.id)
    assert len(first) >= 2
    assert {t.tag for t in first} == {t.tag for t in second}
    with container.uow() as uow:
        rows = uow.asset_tags.list_for_asset(dto.id)
        # Unique on asset+tag+source+version — no duplicates after re-run
        keys = {(r.tag, r.source_model, r.model_version) for r in rows}
        assert len(keys) == len(rows)


def test_tag_job_worker_path_succeeds(container: Container) -> None:
    dto = container.store_asset().execute(
        StoreBytesCommand(
            data=b"worker-tag-path",
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename="w.png",
        )
    )
    runner = ClaimAndRunStubJob(
        container.uow(),
        worker_id=container.settings.worker_id,
        lease_seconds=30,
    )
    claimed = runner.claim()
    assert claimed is not None
    assert claimed.kind == JobKind.TAG_ASSET.value
    tags = container.tag_asset().execute(dto.id)
    done = runner.succeed(claimed.id, progress={"percent": 100, "tag_count": len(tags)})
    assert done.status == JobStatus.SUCCEEDED.value
    listed = container.list_asset_tags().execute(dto.id)
    assert any(t["tag"] == "stub_auto" for t in listed)


def test_visual_library_search_includes_auto_tags(container: Container) -> None:
    from creator_studio.application.e2e.visual_library_seed import seed_visual_library_catalog

    catalog = seed_visual_library_catalog(
        container.uow(),
        container.store_asset(),
        container.seed_marketplace_item(),
    )
    preview_ids = list(catalog.get("preview_asset_ids") or [])
    assert preview_ids
    # Run tagging synchronously (stub) for the first preview asset
    container.tag_asset().execute(preview_ids[0])

    items = VisualLibraryQuery(container.uow()).list_items(q="stub_auto")
    assert len(items) >= 1
    assert any("stub_auto" in (item.get("tags") or []) for item in items)
