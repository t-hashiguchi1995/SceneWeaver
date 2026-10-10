from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from creator_studio.domain.ids import AssetId, new_id
from creator_studio.domain.timeutil import utc_now


class AssetKind(StrEnum):
    IMPORTED = "imported"
    REFERENCE = "reference"
    GENERATED = "generated"
    ADOPTED = "adopted"
    DERIVED = "derived"
    PLATE = "plate"
    POSE = "pose"


class ReviewDecision(StrEnum):
    PENDING = "pending"
    ADOPTED = "adopted"
    REJECTED = "rejected"


DECISION_METADATA_KEY = "review_decision"


@dataclass
class Asset:
    id: AssetId
    sha256: str
    uri: str
    kind: AssetKind
    mime: str
    byte_size: int
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        sha256: str,
        uri: str,
        kind: AssetKind,
        mime: str,
        byte_size: int,
        metadata: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> Asset:
        return cls(
            id=AssetId(new_id()),
            sha256=sha256,
            uri=uri,
            kind=kind,
            mime=mime,
            byte_size=byte_size,
            metadata=metadata or {},
            provenance=provenance or {},
        )

    @property
    def review_decision(self) -> ReviewDecision:
        raw = self.metadata.get(DECISION_METADATA_KEY, ReviewDecision.PENDING.value)
        try:
            return ReviewDecision(str(raw))
        except ValueError:
            return ReviewDecision.PENDING

    def set_review_decision(self, decision: ReviewDecision) -> None:
        self.metadata = {**self.metadata, DECISION_METADATA_KEY: decision.value}
        if decision == ReviewDecision.ADOPTED:
            self.kind = AssetKind.ADOPTED