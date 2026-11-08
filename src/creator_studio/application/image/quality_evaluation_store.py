"""Small JSON store beside assets under the configured runtime directory.

Each file wraps the spec record with optional average-hash and review metadata,
so duplicate lookup and review reasons survive restarts without extending the
public evaluation schema. Callers may override directory for isolated stores.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from creator_studio.application.image.quality_evaluation import QualityEvaluation


def _directory(directory=None) -> Path:
    if directory is None:
        from creator_studio.infrastructure.settings import get_settings

        directory = get_settings().runtime_path() / "quality_evaluations"
    return Path(directory)


def _path(evaluation_id, directory=None) -> Path:
    if not evaluation_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for c in evaluation_id
    ):
        raise FileNotFoundError(evaluation_id)
    return _directory(directory) / f"{evaluation_id}.json"


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = stream.name
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def save_evaluation(record, *, directory=None, image_hash=None):
    path = _path(record.quality_evaluation_id, directory)
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    payload["evaluation"] = record.to_dict()
    if image_hash is not None:
        payload["average_hash"] = image_hash
    _write(path, payload)


def load_evaluation(evaluation_id, *, directory=None):
    payload = json.loads(_path(evaluation_id, directory).read_text(encoding="utf-8"))
    return QualityEvaluation.from_dict(payload["evaluation"])


def list_evaluations(*, directory=None):
    return [
        load_evaluation(p.stem, directory=directory)
        for p in sorted(_directory(directory).glob("*.json"))
    ]


def known_image_hashes(*, directory=None):
    hashes = {}
    for path in sorted(_directory(directory).glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "average_hash" in payload:
            hashes[payload["evaluation"]["quality_evaluation_id"]] = payload["average_hash"]
    return hashes


def save_review(evaluation_id, reviewer_id, verdict, reasons, reviewed_at_iso, *, directory=None):
    path = _path(evaluation_id, directory)
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = QualityEvaluation.from_dict(payload["evaluation"])
    record.reviewer_id = reviewer_id
    record.human_verdict = verdict
    record.reviewed_at = reviewed_at_iso
    payload["evaluation"] = record.to_dict()
    payload["review"] = {
        "reasons": reasons,
        "reviewer_id": reviewer_id,
        "verdict": verdict,
        "reviewed_at": reviewed_at_iso,
    }
    _write(path, payload)
    return record
