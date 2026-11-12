"""Immutable intent recorded before an external submission."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any

from creator_studio.domain.timeutil import utc_now


def make_correlation_key(job_id: str, attempt: int) -> str:
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("job_id must be non-empty")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ValueError("attempt must be an integer >= 1")
    return f"sw-job:{job_id}:attempt:{attempt}"


@dataclass(frozen=True)
class SubmissionIntent:
    job_id: str
    attempt: int
    correlation_key: str
    provider: str = "comfyui"
    snapshot_hash: str | None = None
    intended_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.correlation_key != make_correlation_key(self.job_id, self.attempt):
            raise ValueError("correlation_key does not match job_id and attempt")
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("provider must be non-empty")
        if self.snapshot_hash is not None and (
            not isinstance(self.snapshot_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.snapshot_hash) is None
        ):
            raise ValueError("snapshot_hash must be 64 lowercase hex characters")
        if not isinstance(self.intended_at, datetime):
            raise ValueError("intended_at must be a datetime")  # noqa: TRY004

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["intended_at"] = self.intended_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubmissionIntent:
        if not isinstance(data, dict):
            raise ValueError("SubmissionIntent must be a dict")  # noqa: TRY004
        unknown = data.keys() - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"unknown SubmissionIntent keys: {sorted(map(str, unknown))}")
        values = dict(data)
        try:
            if "intended_at" in values:
                values["intended_at"] = datetime.fromisoformat(values["intended_at"])
            return cls(**values)
        except TypeError as exc:
            raise ValueError(f"invalid SubmissionIntent: {exc}") from exc

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, data: str) -> SubmissionIntent:
        return cls.from_dict(json.loads(data))
