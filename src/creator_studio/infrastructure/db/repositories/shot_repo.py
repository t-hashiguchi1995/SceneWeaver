from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.domain.ids import BeatId, ShotId
from creator_studio.domain.shot import GenerationAttempt, RenderPlan, ShotSpec
from creator_studio.infrastructure.db.models.shot import (
    GenerationAttemptRow,
    RenderPlanRow,
    ShotRow,
)


class SqlAlchemyShotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, shot: ShotSpec) -> ShotSpec:
        self._session.add(self._to_row(shot))
        return shot

    def get(self, shot_id: ShotId | str) -> ShotSpec | None:
        row = self._session.get(ShotRow, str(shot_id))
        return self._from_row(row) if row else None

    def save(self, shot: ShotSpec) -> ShotSpec:
        row = self._session.get(ShotRow, str(shot.id))
        if row is None:
            return self.add(shot)
        fresh = self._to_row(shot)
        row.revision = fresh.revision
        row.render_spec_json = fresh.render_spec_json
        row.stale_reason = fresh.stale_reason
        row.current_prompt_draft_id = fresh.current_prompt_draft_id
        row.updated_at = fresh.updated_at
        return shot

    def list_for_beat(self, beat_id: BeatId | str) -> list[ShotSpec]:
        rows = self._session.scalars(
            select(ShotRow).where(ShotRow.beat_id == str(beat_id))
        ).all()
        return [self._from_row(r) for r in rows]

    def _to_row(self, shot: ShotSpec) -> ShotRow:
        return ShotRow(
            id=str(shot.id),
            beat_id=str(shot.beat_id),
            revision=shot.revision,
            render_spec_json=shot.render_spec,
            stale_reason=shot.stale_reason,
            current_prompt_draft_id=shot.current_prompt_draft_id,
            created_at=shot.created_at,
            updated_at=shot.updated_at,
        )

    def _from_row(self, row: ShotRow) -> ShotSpec:
        return ShotSpec(
            id=ShotId(row.id),
            beat_id=BeatId(row.beat_id),
            revision=row.revision,
            render_spec=dict(row.render_spec_json or {}),
            stale_reason=row.stale_reason,
            current_prompt_draft_id=row.current_prompt_draft_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class SqlAlchemyRenderPlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, plan: RenderPlan) -> RenderPlan:
        self._session.add(
            RenderPlanRow(
                id=plan.id,
                shot_id=str(plan.shot_id),
                shot_revision=plan.shot_revision,
                capability=plan.capability,
                provider=plan.provider,
                template_id=plan.template_id,
                refs_json=plan.refs,
                stale_reason=plan.stale_reason,
                created_at=plan.created_at,
            )
        )
        return plan

    def get(self, plan_id: str) -> RenderPlan | None:
        row = self._session.get(RenderPlanRow, plan_id)
        return self._from_row(row) if row else None

    def save(self, plan: RenderPlan) -> RenderPlan:
        row = self._session.get(RenderPlanRow, plan.id)
        if row is None:
            return self.add(plan)
        row.provider = plan.provider
        row.template_id = plan.template_id
        row.refs_json = plan.refs
        row.stale_reason = plan.stale_reason
        return plan

    def list_for_shot(self, shot_id: ShotId | str) -> list[RenderPlan]:
        rows = self._session.scalars(
            select(RenderPlanRow).where(RenderPlanRow.shot_id == str(shot_id))
        ).all()
        return [self._from_row(r) for r in rows]

    def _from_row(self, row: RenderPlanRow) -> RenderPlan:
        return RenderPlan(
            id=row.id,
            shot_id=ShotId(row.shot_id),
            shot_revision=row.shot_revision,
            capability=row.capability,
            provider=row.provider,
            template_id=row.template_id,
            refs=dict(row.refs_json or {}),
            stale_reason=row.stale_reason,
            created_at=row.created_at,
        )


class SqlAlchemyGenerationAttemptRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, attempt: GenerationAttempt) -> GenerationAttempt:
        self._session.add(
            GenerationAttemptRow(
                id=attempt.id,
                render_plan_id=attempt.render_plan_id,
                based_on_shot_revision=attempt.based_on_shot_revision,
                status=attempt.status,
                seed=attempt.seed,
                payload_json=attempt.payload,
                workflow_hash=attempt.workflow_hash,
                output_asset_ids_json=attempt.output_asset_ids,
                created_at=attempt.created_at,
            )
        )
        return attempt

    def get(self, attempt_id: str) -> GenerationAttempt | None:
        row = self._session.get(GenerationAttemptRow, attempt_id)
        if row is None:
            return None
        return self._from_row(row)

    def list_for_shot(self, shot_id: ShotId | str) -> list[GenerationAttempt]:
        plan_ids = self._session.scalars(
            select(RenderPlanRow.id).where(RenderPlanRow.shot_id == str(shot_id))
        ).all()
        if not plan_ids:
            return []
        rows = self._session.scalars(
            select(GenerationAttemptRow)
            .where(GenerationAttemptRow.render_plan_id.in_(list(plan_ids)))
            .order_by(GenerationAttemptRow.created_at.desc())
        ).all()
        return [self._from_row(r) for r in rows]

    def _from_row(self, row: GenerationAttemptRow) -> GenerationAttempt:
        return GenerationAttempt(
            id=row.id,
            render_plan_id=row.render_plan_id,
            based_on_shot_revision=row.based_on_shot_revision,
            status=row.status,
            seed=row.seed,
            payload=dict(row.payload_json or {}),
            workflow_hash=row.workflow_hash,
            output_asset_ids=list(row.output_asset_ids_json or []),
            created_at=row.created_at,
        )
