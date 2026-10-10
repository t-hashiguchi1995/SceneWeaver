"""Alembic helpers for app bootstrap and tests (no create_all)."""

from __future__ import annotations

import os

from alembic import command
from alembic.config import Config

from creator_studio.infrastructure.settings import clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT


def alembic_config(sqlalchemy_url: str | None = None) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    if sqlalchemy_url is not None:
        cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)
    return cfg


def upgrade_head(sqlalchemy_url: str | None = None) -> None:
    """Apply all migrations. Prefer this over MetaData.create_all for app/tests."""
    if sqlalchemy_url is not None:
        os.environ["SCENEWEAVER_DATABASE_URL"] = sqlalchemy_url
        clear_settings_cache()
    command.upgrade(alembic_config(sqlalchemy_url), "head")
