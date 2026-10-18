from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from creator_studio.application.assets.store_asset import StoreBytesCommand, StoreAssetBytes
from creator_studio.application.projects.create_project import CreateProjectCommand, CreateProject
from creator_studio.application.characters.manage import (
    CreateCharacter,
    UpdatePersona,
    UpdateVisualIdentity,
)
from creator_studio.application.story.manage import CreateBeat, CreateScene
from creator_studio.application.wardrobe.tryon import SeedMarketplaceItem
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId
from creator_studio.domain.wardrobe import MarketplaceItem
from creator_studio.infrastructure.settings.config import REPO_ROOT
from creator_studio.ports.unit_of_work import UnitOfWork

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass
class SeedResult:
    scenario: str
    project_id: str | None = None
    character_id: str | None = None
    scene_id: str | None = None
    beat_id: str | None = None
    marketplace_item_id: str | None = None
    tryon_base_asset_id: str | None = None
    extras: dict[str, Any] | None = None


class E2ESeedService:
    def __init__(
        self,
        uow: UnitOfWork,
        store_asset: StoreAssetBytes,
        create_project: CreateProject,
        create_character: CreateCharacter,
        update_persona: UpdatePersona,
        update_visual: UpdateVisualIdentity,
        create_scene: CreateScene,
        create_beat: CreateBeat,
        seed_market: SeedMarketplaceItem,
    ) -> None:
        self._uow = uow
        self._store = store_asset
        self._create_project = create_project
        self._create_character = create_character
        self._update_persona = update_persona
        self._update_visual = update_visual
        self._create_scene = create_scene
        self._create_beat = create_beat
        self._seed_market = seed_market

    def seed(self, scenario: str) -> SeedResult:
        if scenario == "m1_foundation":
            project = self._create_project.execute(CreateProjectCommand(title="E2E Foundation"))
            return SeedResult(scenario=scenario, project_id=project.id)

        if scenario == "visual_library":
            return self._seed_visual_library()

        if scenario in {"m2_story", "m3_tryon", "m4_visual", "m5_delivery", "vertical_slice"}:
            return self._seed_story_base(scenario)

        raise ValueError(f"unknown scenario: {scenario}")

    def _seed_visual_library(self) -> SeedResult:
        from creator_studio.application.e2e.visual_library_seed import seed_visual_library_catalog

        project = self._create_project.execute(CreateProjectCommand(title="E2E Visual Library"))
        catalog = seed_visual_library_catalog(self._uow, self._store, self._seed_market)
        return SeedResult(
            scenario="visual_library",
            project_id=project.id,
            marketplace_item_id=(catalog["marketplace_item_ids"] or [None])[0],
            extras=catalog,
        )

    def _seed_story_base(self, scenario: str) -> SeedResult:
        project = self._create_project.execute(CreateProjectCommand(title=f"E2E {scenario}"))
        character = self._create_character.execute("リゼヘル")
        self._update_persona.execute(
            character.id,
            {
                "first_person": "私",
                "second_person": "あなた",
                "voice_examples": [
                    {"text": "えへへ、もっと褒めてもいいんですよ？", "polarity": "positive"},
                    {"text": "じゃあ、一緒に行きません？", "polarity": "positive"},
                ],
            },
        )
        base = self._store.execute(
            StoreBytesCommand(
                data=_load_fixture("characters/char_a/canonical_fullbody.png", fallback=_PNG + b"base"),
                kind=AssetKind.REFERENCE,
                mime="image/png",
                relative_dir="characters",
                filename="canonical_fullbody.png",
            )
        )
        self._update_visual.execute(
            character.id,
            {"tryon_base_asset_id": base.id, "hair": "black", "identity_tags": ["1girl"]},
        )
        scene = self._create_scene.execute(
            project.id,
            "Cafe",
            objective="stay together",
            initial_state={},
        )
        beat = self._create_beat.execute(
            scene.id,
            intent="もう少し一緒にいたい",
            subtext="直接寂しいとは言わない",
            emotion={"name": "shy", "intensity": 0.65},
            speaker_id=character.id,
        )

        item_id = None
        extras: dict[str, Any] = {}
        if scenario in {"m3_tryon", "m4_visual", "m5_delivery", "vertical_slice"}:
            plate = self._store.execute(
                StoreBytesCommand(
                    data=_load_fixture("garments/cardigan_plate.png", fallback=_PNG + b"plate"),
                    kind=AssetKind.PLATE,
                    mime="image/png",
                    relative_dir="plates",
                    filename="cardigan.png",
                )
            )
            item = MarketplaceItem.create(
                title="Soft Knit Cardigan",
                category="outerwear",
                region="tops",
                garment_description="soft cream oversized knit cardigan",
                canonical_plate_asset_id=AssetId(plate.id),
                style_tags=["soft", "casual"],
                colors=["cream"],
            )
            self._seed_market.execute(item)
            item_id = item.id

        if scenario in {"m4_visual", "m5_delivery", "vertical_slice"}:
            pose = self._store.execute(
                StoreBytesCommand(
                    data=_load_fixture(
                        "pose/look_over_shoulder_openpose.png",
                        fallback=_PNG + b"pose",
                    ),
                    kind=AssetKind.REFERENCE,
                    mime="image/png",
                    relative_dir="pose",
                    filename="openpose.png",
                )
            )
            extras["pose_asset_id"] = pose.id
            extras["pose_asset_uri"] = pose.uri

        return SeedResult(
            scenario=scenario,
            project_id=project.id,
            character_id=character.id,
            scene_id=scene.id,
            beat_id=beat.id,
            marketplace_item_id=item_id,
            tryon_base_asset_id=base.id,
            extras=extras or None,
        )


def _load_fixture(relative: str, *, fallback: bytes) -> bytes:
    path = REPO_ROOT / "tests" / "fixtures" / relative
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fallback)
    return fallback


def reset_runtime(runtime_dir: Path, *, database_url: str | None = None) -> None:
    """Clear E2E runtime artifacts without deleting the SQLite file inode.

    The long-lived worker process keeps an open handle to studio.db. Replacing
    the file (rmtree) leaves the worker reading a deleted inode while the API
    writes to a new one — jobs stay forever queued. Wipe rows + dirs in place.
    """
    import shutil

    from sqlalchemy import create_engine, text

    runtime_dir.mkdir(parents=True, exist_ok=True)
    for name in ("assets", "projects", "logs", "jobs", "csp_handoff"):
        path = runtime_dir / name
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    db_path = runtime_dir / "studio.db"
    url = database_url or f"sqlite:///{db_path}"
    if not db_path.exists() and url.startswith("sqlite:///"):
        return

    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            tables = conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' "
                    "AND name NOT LIKE '%_fts_%' "
                    "AND name != 'alembic_version'"
                )
            ).fetchall()
            for (name,) in tables:
                if name.endswith("_fts") or name.startswith("marketplace_items_fts"):
                    # FTS5 virtual tables: recreate empty content via delete
                    conn.execute(text(f'DELETE FROM "{name}"'))
                else:
                    conn.execute(text(f'DELETE FROM "{name}"'))
            # Ensure FTS row sync even if named oddly
            try:
                conn.execute(text("DELETE FROM marketplace_items_fts"))
            except Exception:  # noqa: BLE001
                pass
            conn.execute(text("PRAGMA foreign_keys=ON"))
    finally:
        engine.dispose()