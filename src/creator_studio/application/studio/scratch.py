"""Quick Image Studio — Scratch Shot lifecycle (Phase 1).

materialize = copy generation state, not rerender.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.asset import AssetKind
from creator_studio.infrastructure.container import Container

ScratchLifecycle = Literal["draft", "generated", "adopted", "abandoned"]

_STUDIO_KEY = "_studio"
_SCRATCH_PROJECT_TITLE = "Quick Studio Scratch"


def studio_meta(render_spec: dict[str, Any]) -> dict[str, Any]:
    raw = render_spec.get(_STUDIO_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


class ScratchStudioService:
    def __init__(self, container: Container) -> None:
        self._c = container

    def create_session(
        self,
        *,
        character_id: str,
        outfit_profile_id: str | None = None,
        capability: str = "BaseRender",
    ) -> dict[str, Any]:
        project = self._find_or_create_scratch_project()
        scene = self._c.create_scene().execute(project.id, "Studio Scratch")
        beat = self._c.create_beat().execute(
            scene.id, intent="quick studio scratch", speaker_id=character_id
        )
        pipe = self._c.shot_pipeline()
        shot = pipe.plan_shot(beat.id)
        render_patch: dict[str, Any] = {
            "capability": capability,
            "character_id": character_id,
            "content_rating": "general",
            _STUDIO_KEY: {
                "source": "quick_studio",
                "hidden": True,
                "lifecycle": "draft",
                "formal_shot_id": None,
                "formal_project_id": None,
            },
        }
        if outfit_profile_id:
            render_patch["outfit_profile_id"] = outfit_profile_id
        shot = pipe.update_shot(shot.id, render_patch)
        self._c.prompt_draft_service().ensure_for_shot(shot.id)
        return self._session_view(shot.id)

    def get_session(self, shot_id: str) -> dict[str, Any]:
        return self._session_view(shot_id)

    def set_lifecycle(self, shot_id: str, lifecycle: ScratchLifecycle) -> dict[str, Any]:
        pipe = self._c.shot_pipeline()
        shot = pipe.get_shot(shot_id)
        meta = studio_meta(shot.render_spec)
        if meta.get("source") != "quick_studio":
            raise ValueError("not a quick studio scratch shot")
        if lifecycle == "abandoned" and meta.get("lifecycle") == "adopted":
            raise ValueError("cannot abandon adopted scratch; keep for history")
        meta["lifecycle"] = lifecycle
        pipe.update_shot(shot_id, {_STUDIO_KEY: meta})
        return self._session_view(shot_id)

    def mark_generated(self, shot_id: str) -> dict[str, Any]:
        return self.set_lifecycle(shot_id, "generated")

    def abandon(self, shot_id: str) -> dict[str, Any]:
        return self.set_lifecycle(shot_id, "abandoned")

    def materialize_to_story(
        self,
        shot_id: str,
        *,
        project_id: str | None = None,
        generation_attempt_id: str | None = None,
    ) -> dict[str, Any]:
        """Copy generation state onto a Formal Story Shot — do not rerender."""
        pipe = self._c.shot_pipeline()
        scratch = pipe.get_shot(shot_id)
        meta = studio_meta(scratch.render_spec)
        if meta.get("source") != "quick_studio":
            raise ValueError("not a quick studio scratch shot")
        if meta.get("lifecycle") == "abandoned":
            raise ValueError("cannot materialize abandoned scratch")

        attempt_id = generation_attempt_id or self._latest_attempt_id(shot_id)
        if not attempt_id:
            raise ValueError("no generation to adopt; generate first")

        attempt = pipe.get_attempt(attempt_id)
        if not attempt.output_asset_ids:
            raise ValueError("generation has no output assets")

        # Formal project/scene/beat
        if project_id:
            with self._c.uow() as uow:
                project = uow.projects.get(project_id)
                if project is None:
                    raise ValueError("project not found")
            formal_project_id = project_id
        else:
            project = self._c.create_project().execute(
                CreateProjectCommand(title="Quick Studio Adopted")
            )
            formal_project_id = project.id

        scene = self._c.create_scene().execute(formal_project_id, "Adopted from Studio")
        character_id = scratch.render_spec.get("character_id")
        beat = self._c.create_beat().execute(
            scene.id,
            intent="adopted from quick studio",
            speaker_id=str(character_id) if character_id else None,
        )
        formal = pipe.plan_shot(beat.id)

        # COPY render_spec (without scratch flags) + link assets via render_from_attempt pattern
        copied_spec = deepcopy(scratch.render_spec)
        copied_spec.pop(_STUDIO_KEY, None)
        copied_spec["_adopted_from_scratch_shot_id"] = shot_id
        copied_spec["_adopted_generation_attempt_id"] = attempt_id
        formal = pipe.update_shot(formal.id, copied_spec)

        # Ensure prompt draft mirrors scratch final prompts
        drafts = self._c.prompt_draft_service()
        drafts.ensure_for_shot(formal.id)
        snap_pos = attempt.payload.get("final_positive_prompt")
        snap_neg = attempt.payload.get("final_negative_prompt")
        if isinstance(snap_pos, str) and isinstance(snap_neg, str):
            drafts.update_edits(formal.id, snap_pos, snap_neg)

        # Attach outputs by creating a replay-style attempt record pointing at same assets
        pipe.attach_adopted_outputs(
            formal.id,
            source_attempt_id=attempt_id,
            output_asset_ids=list(attempt.output_asset_ids),
            payload_overlay={
                "materialize": "copy_generation_state",
                "source_scratch_shot_id": shot_id,
            },
        )

        meta["lifecycle"] = "adopted"
        meta["formal_shot_id"] = formal.id
        meta["formal_project_id"] = formal_project_id
        pipe.update_shot(shot_id, {_STUDIO_KEY: meta})

        return {
            **self._session_view(shot_id),
            "formal_shot_id": formal.id,
            "formal_project_id": formal_project_id,
            "generation_attempt_id": attempt_id,
            "output_asset_ids": list(attempt.output_asset_ids),
        }

    def apply_pose(
        self,
        shot_id: str,
        *,
        pose_id: str,
        pose_view: str,
        flipped: bool = False,
        control_strength: float = 1.0,
    ) -> dict[str, Any]:
        refs = self._c.reference_pose_service()
        detail = refs.get_detail(pose_id)
        if detail is None:
            raise ValueError("pose not found")
        view = (detail.get("views") or {}).get(pose_view)
        if view is None:
            raise ValueError("pose view not found")
        snap = refs.build_pose_provenance(
            pose_id=pose_id,
            pose_view=pose_view,
            flipped=flipped,
            control_strength=control_strength,
        )
        assert snap is not None
        line = (view.get("references") or {}).get("line") or {}
        use_pose = snap["pose_method"] == "reference_image"
        patch: dict[str, Any] = {
            "pose": {
                "id": pose_view if not use_pose else pose_id,
                "pose_id": pose_id,
                "pose_view": pose_view,
                "pose_prompt": view.get("prompt") or "",
                "control_strength": control_strength,
                "flipped": flipped,
            },
            "pose_provenance": snap,
            "control_strength": control_strength,
        }
        # Prompt-only: keep capability; reference image → PoseControlledRender + asset:// URI
        if use_pose:
            patch["capability"] = "PoseControlledRender"
            pose_uri = self._ensure_pose_asset_uri(pose_id=pose_id, pose_view=pose_view, line=line)
            patch["pose_asset_uri"] = pose_uri
            if line.get("sha256"):
                patch["pose"]["line_sha256"] = line["sha256"]
        else:
            patch["pose_asset_uri"] = None
        pipe = self._c.shot_pipeline()
        pipe.update_shot(shot_id, patch)
        # Rebuild prompt so pose_prompt compiles into Anima tags when prompt-only
        drafts = self._c.prompt_draft_service()
        drafts.ensure_for_shot(shot_id)
        try:
            drafts.rebuild(shot_id, confirm=True)
        except ValueError:
            pass
        # If prompt-only, merge pose prompt into edited positive lightly via ensure base
        return self._session_view(shot_id)

    def _ensure_pose_asset_uri(
        self,
        *,
        pose_id: str,
        pose_view: str,
        line: dict[str, Any],
    ) -> str | None:
        """Materialize Shisei line art into AssetStore so Comfy gets asset:// pose_image."""
        url = str(line.get("url") or "")
        # Detail DTO exposes API path; recover relative pack path after /references/assets/
        marker = "/api/v1/references/assets/"
        rel = url.split(marker, 1)[-1] if marker in url else ""
        if not rel:
            # Fall back via provider using pose definition
            pose = self._c.reference_pose_service().provider.get_pose(pose_id)
            view_obj = pose.views.get(pose_view) if pose else None
            if view_obj and view_obj.line:
                rel = view_obj.line.relative_path
        if not rel:
            return None
        resolved = self._c.reference_pose_service().resolve_asset_bytes(rel)
        if resolved is None:
            return None
        data, mime = resolved
        stored = self._c.store_asset().execute(
            StoreBytesCommand(
                data=data,
                kind=AssetKind.REFERENCE,
                mime=mime or "image/webp",
                relative_dir="pose/shisei",
                filename=f"{pose_id}-{pose_view}.webp",
            )
        )
        return stored.uri

    def _find_or_create_scratch_project(self) -> Any:
        projects = self._c.list_projects().execute()
        for p in projects:
            if p.title == _SCRATCH_PROJECT_TITLE:
                return p
        return self._c.create_project().execute(
            CreateProjectCommand(title=_SCRATCH_PROJECT_TITLE)
        )

    def _session_view(self, shot_id: str) -> dict[str, Any]:
        pipe = self._c.shot_pipeline()
        shot = pipe.get_shot(shot_id)
        meta = studio_meta(shot.render_spec)
        draft = None
        try:
            draft = self._c.prompt_draft_service().get_for_shot(shot_id).to_dict()
        except ValueError:
            draft = None
        return {
            "shot_id": shot.id,
            "beat_id": shot.beat_id,
            "revision": shot.revision,
            "lifecycle": meta.get("lifecycle", "draft"),
            "hidden": bool(meta.get("hidden", True)),
            "source": meta.get("source", "quick_studio"),
            "formal_shot_id": meta.get("formal_shot_id"),
            "formal_project_id": meta.get("formal_project_id"),
            "render_spec": shot.render_spec,
            "prompt_draft": draft,
            "pose_provenance": shot.render_spec.get("pose_provenance"),
        }

    def _latest_attempt_id(self, shot_id: str) -> str | None:
        pipe = self._c.shot_pipeline()
        history = pipe.list_attempts_for_shot(shot_id)
        # list is newest-first
        for item in history:
            if item.get("status") == "succeeded" and item.get("output_asset_ids"):
                return str(item["id"])
        return None
