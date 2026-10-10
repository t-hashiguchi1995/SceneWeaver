from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.wardrobe import MarketplaceItem
from creator_studio.infrastructure.container import Container
from creator_studio.infrastructure.db import models as _models  # noqa: F401
from creator_studio.infrastructure.db.base import Base
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings


EXPECTED_TABLES = {
    "projects",
    "jobs",
    "assets",
    "asset_links",
    "characters",
    "scenes",
    "beats",
    "script_events",
    "marketplace_items",
    "outfit_profiles",
    "tryon_sessions",
    "shots",
    "render_plans",
    "generation_attempts",
}


def test_alembic_upgrade_matches_metadata_and_accepts_fixtures(settings: Settings) -> None:
    """Empty DB → alembic upgrade head → schema == metadata → M1–M5 seed works."""
    url = settings.sqlalchemy_url()
    upgrade_head(url)
    reset_engine()

    engine = create_engine(url)
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names()) - {"alembic_version"}

    missing = EXPECTED_TABLES - db_tables
    assert not missing, f"migration missing tables: {sorted(missing)}"

    for table_name, table in Base.metadata.tables.items():
        assert table_name in db_tables, f"ORM table {table_name} not in DB after migrate"
        db_cols = {c["name"] for c in inspector.get_columns(table_name)}
        model_cols = {c.name for c in table.columns}
        assert model_cols == db_cols, (
            f"{table_name} column mismatch: "
            f"model-only={sorted(model_cols - db_cols)} "
            f"db-only={sorted(db_cols - model_cols)}"
        )

    with engine.connect() as conn:
        fts = conn.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='marketplace_items_fts'"
            )
        ).scalar()
        assert fts == "marketplace_items_fts"

    upgrade_head(url)  # idempotent
    reset_engine()

    container = Container(settings)
    project = container.create_project().execute(
        CreateProjectCommand(title="Migrate Fixture Project")
    )
    character = container.create_character().execute("Aiko")
    scene = container.create_scene().execute(
        project_id=project.id, title="Cafe", objective="meet"
    )
    beat = container.create_beat().execute(scene_id=scene.id, intent="greet", action="wave")
    item = MarketplaceItem.create(
        title="Summer Dress",
        category="dress",
        region="upper",
        style_tags=["casual", "summer"],
        garment_description="light cotton dress",
    )
    container.seed_marketplace_item().execute(item)

    assert project.id
    assert character.id
    assert beat.id
    hits = container.search_market().execute(query="summer")
    assert any(h["id"] == item.id for h in hits)


def test_capabilities_only_approved_models(container: Container) -> None:
    caps = container.capabilities().list_capabilities()
    assert "BaseRender" in caps
    assert "OutfitTryOn" in caps
    assert caps["BaseRender"].configured is True
    assert caps["BaseRender"].model_id == "anima_base"
    assert caps["BaseRender"].runtime_available is True
    assert caps["BaseRender"].detail == "fake backend"
    assert container.capabilities().resolve_model("OutfitTryOn") == "qwen_image_edit_2509"


def test_application_capabilities_have_no_httpx_import() -> None:
    import creator_studio.application.capabilities.resolve as mod

    assert not hasattr(mod, "httpx")
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "httpx" not in source
    assert "comfy_url" not in source
