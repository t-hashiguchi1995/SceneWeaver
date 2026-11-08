"""Atomic JSON files beside the runtime asset directory."""

import json
from pathlib import Path

from creator_studio.application.image.quality_evaluation_store import _write
from creator_studio.application.lettering.models import LetteringLayout


def _path(layout_id, directory=None):
    if not layout_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for c in layout_id
    ):
        raise FileNotFoundError(layout_id)
    if directory is None:
        from creator_studio.infrastructure.settings import get_settings

        directory = get_settings().runtime_path() / "lettering_layouts"
    return Path(directory) / f"{layout_id}.json"


def save_layout(layout, *, directory=None):
    _write(_path(layout.layout_id, directory), layout.to_dict())


def load_layout(layout_id, *, directory=None):
    return LetteringLayout.from_dict(
        json.loads(_path(layout_id, directory).read_text(encoding="utf-8"))
    )


get_layout = load_layout
