from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import yaml

from creator_studio.application.image.runner import candidate_count_for_backend, submit_wait_collect
from creator_studio.domain.asset import Asset, AssetKind
from creator_studio.domain.ids import BeatId
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


class PromptCompiler:
    def compile_anima(self, render_spec: dict[str, Any]) -> dict[str, str]:
        identity = ",".join(render_spec.get("identity_tags", ["1girl"]))
        outfit = render_spec.get("outfit_tags", "casual clothes")
        expression = render_spec.get("expression", {}).get("id", "neutral")
        pose = render_spec.get("pose", {}).get("id", "standing")
        camera = render_spec.get("camera", {})
        positive = (
            "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, "
            f"safe, @fuzichoco, @rella, {identity}, {outfit}, {expression}, {pose}, "
            f"{camera.get('shot', 'medium')}, {camera.get('angle', 'eye_level')}"
        )
        negative = (
            "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, "
            "sepia, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
            "fewer digits, cropped, signature, watermark, username, artist name"
        )
        return {"positive": positive, "negative": negative}


class ShotPipeline:
    def __init__(
        self,
        uow: UnitOfWork,
        llm: LLMGateway,
        image: ImageBackend,
        store: AssetStore,
        prompts: PromptRegistry | None = None,
    ) -> None:
        self._uow = uow
        self._llm = llm
        self._image = image
        self._store = store
        self._prompts = prompts or PromptRegistry()
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
            template_id = "anima_pose_v1" if use_pose else "anima_base_v1"
            model_id, _ = resolve_template_id_for_capability(capability)
            compiled = self._compiler.compile_anima(shot.render_spec)
            plan = RenderPlan.create(
                shot.id,
                shot.revision,
                capability=capability,
                provider="pending",
                template_id=template_id,
                refs={"pose": pose_asset_uri} if pose_asset_uri else {},
            )
            uow.render_plans.add(plan)
            slots: dict[str, Any] = {
                "positive_prompt": compiled["positive"],
                "negative_prompt": compiled["negative"],
                "candidate_count": candidate_count_for_backend(self._image),
            }
            if pose_asset_uri:
                slots["pose_image"] = pose_asset_uri
                slots["control_strength"] = float(
                    shot.render_spec.get("control_strength", 1.0)
                )
            dto = RenderPlanDTO(
                capability=capability,
                template_id=template_id,
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
                    workflow_hash = self._fallback_workflow_hash(template_id, slots)
                provenance: dict[str, Any] = {
                    "shot_id": str(shot.id),
                    "based_on_shot_revision": shot.revision,
                    "provider": meta.get("provider") or ref.provider,
                    "workflow_template_id": meta.get("workflow_template_id") or template_id,
                    "template_id": template_id,
                    "workflow_hash": workflow_hash,
                    "model_id": meta.get("model_id") or model_id,
                    "seed": meta.get("seed", 1234),
                    "external_job_ref": meta.get("external_job_ref") or ref.ref,
                    "prompt_version": "anima_compiler_v1",
                    "compiled": compiled,
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
                workflow_hash = self._fallback_workflow_hash(template_id, slots)

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
            }

    def get_attempt(self, attempt_id: str) -> GenerationAttempt:
        with self._uow as uow:
            attempt = uow.generation_attempts.get(attempt_id)
            if attempt is None:
                raise ValueError("attempt not found")
            return attempt

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
        )

    @staticmethod
    def _fallback_workflow_hash(template_id: str, slots: dict[str, Any]) -> str:
        payload = {"template": template_id, "slots": slots}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
