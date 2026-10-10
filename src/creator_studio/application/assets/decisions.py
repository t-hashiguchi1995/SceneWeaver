from __future__ import annotations

from creator_studio.domain.asset import ReviewDecision
from creator_studio.domain.ids import AssetId
from creator_studio.ports.unit_of_work import UnitOfWork


class SetAssetDecision:
    """Mark a generated/derived asset as adopted or rejected for Review → CSP."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, asset_id: str, decision: str) -> dict[str, str]:
        try:
            parsed = ReviewDecision(decision)
        except ValueError as exc:
            raise ValueError("decision must be 'adopted' or 'rejected'") from exc
        if parsed == ReviewDecision.PENDING:
            raise ValueError("decision must be 'adopted' or 'rejected'")

        with self._uow as uow:
            asset = uow.assets.get(AssetId(asset_id))
            if asset is None:
                raise ValueError("asset not found")
            # Do not rewrite provenance; only decision metadata / kind.
            asset.set_review_decision(parsed)
            uow.assets.save(asset)
            uow.commit()
            return {
                "asset_id": str(asset.id),
                "decision": asset.review_decision.value,
                "sha256": asset.sha256,
            }
