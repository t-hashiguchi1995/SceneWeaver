from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import yaml

from creator_studio.application.image.runner import candidate_count_for_backend, submit_wait_collect
from creator_studio.application.prompt.renderer import PromptRenderer
from creator_studio.domain.asset import Asset, AssetKind, ReviewDecision
from creator_studio.domain.ids import BeatId
from creator_studio.domain.prompt import PromptDraft, compute_context_hash, compute_prompt_hash
from creator_studio.domain.shot import GenerationAttempt, RenderPlan, ShotSpec
from creator_studio.domain.timeutil import utc_now
from creator_studio.infrastructure.prompts import PromptRegistry
from creator_studio.infrastructure.settings.config import REPO_ROOT
from creator_studio.infrastructure.workflows.registry_models import resolve_template_id_for_capability
from creator_studio.ports.asset_store import AssetStore
from creator_studio.ports.image_backend import ImageBackend, RenderPlanDTO
from creator_studio.ports.llm import LLMGateway
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class ShotDTO:
    id: str
    beat_id: str
    revision: int
    render_spec: dict[str, Any]
    stale_reason: str | None
    current_prompt_draft_id: str | None = None


# Back-compat alias used by older tests / imports
class PromptCompiler:
    def __init__(self) -> None:
        self._renderer = PromptRenderer()

    def compile_anima(self, render_spec: dict[str, Any]) -> dict[str, str]:
        rendered = self._renderer.render_anima(render_spec)
        return {"positive": rendered.positive, "negative": rendered.negative}


class ShotPipeline:
    def __init__(
        self,
        uow: UnitOfWork,
        llm: LLMGateway,
        image: ImageBackend,
        store: AssetStore,
        prompts: PromptRegistry | None = None,
        renderer: PromptRenderer | None = None,
    ) -> None:
        self._uow = uow
        self._llm = llm
        self._image = image
        self._store = store
        self._prompts = prompts or PromptRegistry()
        self._renderer = renderer or PromptRenderer()
        self._compiler = PromptCompiler()

    def plan_shot(self, beat_id: str) -> ShotDTO:
        with self._uow as uow:
            beat = uow.beats.get(BeatId(beat_id))
            if beat is None:
                raise ValueError("beat not found")
            user = self._prompts.render(
                "visual/shot_planner_v1.jinja2",
                beat_json=json.dumps(
                    {
                        "intent": beat.intent,
                        "subtext": beat.subtext,
                        "emotion": {"name": beat.emotion.name, "intensity": beat.emotion.intensity},
                    },
                    ensure_ascii=False,
                ),
            )
            spec = self._llm.complete_json(
                system="Convert the locked Beat into a visual shot specification. Return JSON only.",
                user=user + "\nshot specification",
            )
            assert isinstance(spec, dict)
            shot = ShotSpec.create(BeatId(beat_id), spec, revision=1)
            uow.shots.add(shot)
            uow.commit()
            return self._dto(shot)

    def update_shot(self, shot_id: str, patch: dict[str, Any]) -> ShotDTO:
        with self._uow as uow:
            shot = uow.shots.get(shot_id)
            if shot is None:
                raise ValueError("shot not found")
            if shot.is_stale:
                raise ValueError("shot is stale; create a new revision")
            shot.render_spec = {**shot.render_spec, **patch}
            shot.updated_at = utc_now()
            uow.shots.save(shot)
            uow.commit()
            return self._dto(shot)

    def invalidate_for_script_change(self, beat_id: str, reason: str = "script_revision") -> None:
        with self._uow as uow:
            for shot in uow.shots.list_for_beat(beat_id):
                if shot.is_stale:
                    continue
                shot.mark_stale(reason)
                uow.shots.save(shot)
                for plan in uow.render_plans.list_for_shot(shot.id):
                    if plan.stale_reason is None:
                        plan.stale_reason = reason
                        uow.render_plans.save(plan)
            uow.commit()

    def render(self, shot_id: str, *, use_pose: bool = False, pose_asset_uri: str | None = None) -> dict[str, Any]:
        with self._uow as uow:
            shot = uow.shots.get(shot_id)
            if shot is None:
                raise ValueError("shot not found")
            if shot.is_stale:
                raise ValueError("cannot render stale shot")
            capability = "PoseControlledRender" if use_pose else "BaseRender"
            workflow_template_id = "anima_pose_v1" if use_pose else "anima_base_v1"
            model_id, _ = resolve_template_id_for_capability(capability)

            draft = self._ensure_draft_in_uow(uow, shot)
            # ADR 0010: same final strings → prompt_hash and ImageBackend (byte-for-byte).
            final_positive = draft.edited_positive
            final_negative = draft.edited_negative
            prompt_hash = compute_prompt_hash(final_positive, final_negative)
            compiled = {"positive": final_positive, "negative": final_negative}

            plan = RenderPlan.create(
                shot.id,
                shot.revision,
                capability=capability,
                provider="pending",
                template_id=workflow_template_id,
                refs={"pose": pose_asset_uri} if pose_asset_uri else {},
            )
            uow.render_plans.add(plan)
            slots: dict[str, Any] = {
                "positive_prompt": final_positive,
                "negative_prompt": final_negative,
                "candidate_count": candidate_count_for_backend(self._image),
            }
            if pose_asset_uri:
                slots["pose_image"] = pose_asset_uri
                slots["control_strength"] = float(
                    shot.render_spec.get("control_strength", 1.0)
                )
            dto = RenderPlanDTO(
                capability=capability,
                template_id=workflow_template_id,
                seed=1234,
                slots=slots,
                refs=plan.refs,
            )
            validation = self._image.validate(dto)
            if not validation.ok:
                raise ValueError("; ".join(validation.errors))
            ref, artifacts = submit_wait_collect(self._image, dto)
            plan.provider = ref.provider
            uow.render_plans.save(plan)

            control_model = None
            if use_pose:
                registry = yaml.safe_load(
                    (REPO_ROOT / "config" / "model_registry.yaml").read_text(encoding="utf-8")
                ) or {}
                control_model = (registry.get("models") or {}).get(model_id, {}).get(
                    "control_model"
                )

            prompt_snapshot = {
                "template_id": draft.template_id,
                "template_version": draft.template_version,
                "source_kind": draft.source_kind,
                "source_ref": draft.source_ref,
                "rendered_base_positive": draft.rendered_base_positive,
                "rendered_base_negative": draft.rendered_base_negative,
                "final_positive_prompt": final_positive,
                "final_negative_prompt": final_negative,
                "prompt_hash": prompt_hash,
                "modified": draft.modified,
                "prompt_draft_id": draft.id,
            }

            outputs: list[str] = []
            workflow_hash = ""
            for artifact in artifacts:
                meta = artifact.metadata or {}
                workflow_hash = str(meta.get("workflow_hash") or workflow_hash)
                blob = self._store.put_bytes(
                    artifact.bytes_data,
                    relative_dir="generated",
                    filename="shot.png",
                )
                existing = uow.assets.find_by_sha256(blob.sha256)
                if existing:
                    outputs.append(str(existing.id))
                    continue
                if not workflow_hash:
                    workflow_hash = self._fallback_workflow_hash(workflow_template_id, slots)
                provenance: dict[str, Any] = {
                    "shot_id": str(shot.id),
                    "based_on_shot_revision": shot.revision,
                    "provider": meta.get("provider") or ref.provider,
                    "workflow_template_id": meta.get("workflow_template_id") or workflow_template_id,
                    "workflow_hash": workflow_hash,
                    "model_id": meta.get("model_id") or model_id,
                    "seed": meta.get("seed", 1234),
                    "external_job_ref": meta.get("external_job_ref") or ref.ref,
                    "prompt_version": draft.template_version,
                    "compiled": compiled,
                    **prompt_snapshot,
                }
                if use_pose:
                    provenance["pose_asset_uri"] = pose_asset_uri
                    provenance["control_model"] = control_model
                    provenance["control_strength"] = slots.get("control_strength", 1.0)
                asset = Asset.create(
                    sha256=blob.sha256,
                    uri=blob.uri,
                    kind=AssetKind.GENERATED,
                    mime=artifact.mime,
                    byte_size=blob.byte_size,
                    provenance=provenance,
                )
                uow.assets.add(asset)
                outputs.append(str(asset.id))
            if not workflow_hash:
                workflow_hash = self._fallback_workflow_hash(workflow_template_id, slots)

            attempt = GenerationAttempt.create(
                plan.id,
                shot.revision,
                seed=1234,
                payload={
                    "compiled": compiled,
                    "capability": capability,
                    "external_job_ref": ref.ref,
                    "provider": ref.provider,
                    "model_id": model_id,
                    **prompt_snapshot,
                },
                workflow_hash=workflow_hash,
                output_asset_ids=outputs,
            )
            uow.generation_attempts.add(attempt)
            uow.commit()
            return {
                "shot_id": str(shot.id),
                "shot_revision": shot.revision,
                "render_plan_id": plan.id,
                "generation_attempt_id": attempt.id,
                "output_asset_ids": outputs,
                "workflow_hash": workflow_hash,
                "external_job_ref": ref.ref,
                "provider": ref.provider,
                "is_current": attempt.is_current_for(shot.revision),
                "prompt_hash": prompt_hash,
                "final_positive_prompt": final_positive,
                "final_negative_prompt": final_negative,
            }

    def _ensure_draft_in_uow(self, uow: UnitOfWork, shot: ShotSpec) -> PromptDraft:
        rendered = self._renderer.render_anima(shot.render_spec)
        if shot.current_prompt_draft_id:
            draft = uow.prompt_drafts.get(shot.current_prompt_draft_id)
            if draft is not None:
                return draft
        existing = uow.prompt_drafts.get_for_shot_template(
            shot.id, rendered.template_id, rendered.template_version
        )
        if existing is not None:
            shot.current_prompt_draft_id = existing.id
            uow.shots.save(shot)
            return existing
        draft = PromptDraft.create(
            shot.id,
            template_id=rendered.template_id,
            template_version=rendered.template_version,
            source_kind=rendered.source_kind,
            source_ref=rendered.source_ref,
            source_shot_revision=shot.revision,
            context_hash=compute_context_hash(
                shot_revision=shot.revision,
                render_spec=shot.render_spec,
                template_id=rendered.template_id,
                template_version=rendered.template_version,
            ),
            rendered_base_positive=rendered.positive,
            rendered_base_negative=rendered.negative,
        )
        uow.prompt_drafts.add(draft)
        shot.current_prompt_draft_id = draft.id
        uow.shots.save(shot)
        return draft

    def get_attempt(self, attempt_id: str) -> GenerationAttempt:
        with self._uow as uow:
            attempt = uow.generation_attempts.get(attempt_id)
            if attempt is None:
                raise ValueError("attempt not found")
            return attempt

    def list_attempts_for_shot(self, shot_id: str) -> list[dict[str, Any]]:
        with self._uow as uow:
            shot = uow.shots.get(shot_id)
            if shot is None:
                raise ValueError("shot not found")
            attempts = uow.generation_attempts.list_for_shot(shot_id)
            out: list[dict[str, Any]] = []
            for attempt in attempts:
                plan = uow.render_plans.get(attempt.render_plan_id)
                decisions: dict[str, str] = {}
                for asset_id in attempt.output_asset_ids:
                    asset = uow.assets.get(asset_id)
                    if asset is not None and asset.review_decision != ReviewDecision.PENDING:
                        decisions[asset_id] = asset.review_decision.value
                payload = attempt.payload
                out.append(
                    {
                        "id": attempt.id,
                        "render_plan_id": attempt.render_plan_id,
                        "based_on_shot_revision": attempt.based_on_shot_revision,
                        "status": attempt.status,
                        "seed": attempt.seed,
                        "payload": payload,
                        "workflow_hash": attempt.workflow_hash,
                        "output_asset_ids": attempt.output_asset_ids,
                        "created_at": attempt.created_at.isoformat(),
                        "is_current": attempt.is_current_for(shot.revision),
                        "capability": (plan.capability if plan else payload.get("capability")),
                        "workflow_template_id": (
                            plan.template_id if plan else payload.get("workflow_template_id")
                        ),
                        "model_id": payload.get("model_id"),
                        "final_positive_prompt": payload.get("final_positive_prompt"),
                        "final_negative_prompt": payload.get("final_negative_prompt"),
                        "prompt_hash": payload.get("prompt_hash"),
                        "source_kind": payload.get("source_kind"),
                        "source_ref": payload.get("source_ref"),
                        "template_id": payload.get("template_id"),
                        "template_version": payload.get("template_version"),
                        "modified": bool(payload.get("modified")),
                        "asset_decisions": decisions,
                    }
                )
            return out

    def get_shot(self, shot_id: str) -> ShotDTO:
        with self._uow as uow:
            shot = uow.shots.get(shot_id)
            if shot is None:
                raise ValueError("shot not found")
            return self._dto(shot)

    def get_plan(self, plan_id: str) -> RenderPlan:
        with self._uow as uow:
            plan = uow.render_plans.get(plan_id)
            if plan is None:
                raise ValueError("render plan not found")
            return plan

    def current_shot_revision(self, shot_id: str) -> int:
        with self._uow as uow:
            shot = uow.shots.get(shot_id)
            if shot is None:
                raise ValueError("shot not found")
            return shot.revision

    def _dto(self, shot: ShotSpec) -> ShotDTO:
        return ShotDTO(
            id=str(shot.id),
            beat_id=str(shot.beat_id),
            revision=shot.revision,
            render_spec=shot.render_spec,
            stale_reason=shot.stale_reason,
            current_prompt_draft_id=shot.current_prompt_draft_id,
        )

    @staticmethod
    def _fallback_workflow_hash(template_id: str, slots: dict[str, Any]) -> str:
        payload = {"template": template_id, "slots": slots}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
