"""Atomic evaluation JSONs using the lettering store's paths and writer."""

import json

from .store import _path, _write


def _directory(directory):
    if directory is not None:
        return directory
    from creator_studio.infrastructure.settings import get_settings

    return get_settings().runtime_path() / "lettering_quality"


def save_evaluation(evaluation, *, directory=None):
    _write(_path(evaluation["quality_evaluation_id"], _directory(directory)), evaluation)


def load_evaluation(evaluation_id, *, directory=None):
    return json.loads(_path(evaluation_id, _directory(directory)).read_text(encoding="utf-8"))
