"""Quick Image Studio — Scratch Shot lifecycle (Phase 1).

materialize = copy generation state, not rerender.
"""

from __future__ import annotations

import io
from copy import deepcopy
from typing import Any, Literal

from PIL import Image

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.asset import AssetKind
from creator_studio.infrastructure.container import Container

ScratchLifecycle = Literal["draft", "generated", "adopted", "abandoned"]

_STUDIO_KEY = "_studio"
_SCRATCH_PROJECT_TITLE = "Quick Studio Scratch"

# model_profile → initial capability (Pose apply may upgrade to PoseControlledRender)
_MODEL_PROFILES: dict[str, str] = {
    "anima": "BaseRender",
}


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
        model_profile: str = "anima",
        capability: str | None = None,
    ) -> dict[str, Any]:
        profile = (model_profile or "anima").strip().lower()
        if profile not in _MODEL_PROFILES:
            raise ValueError(f"unsupported model_profile: {model_profile}")
        resolved_capability = capability or _MODEL_PROFILES[profile]
        project = self._find_or_create_scratch_project()
        scene = self._c.create_scene().execute(project.id, "Studio Scratch")
        beat = self._c.create_beat().execute(
            scene.id, intent="quick studio scratch", speaker_id=character_id
        )
        pipe = self._c.shot_pipeline()
        shot = pipe.plan_shot(beat.id)
        render_patch: dict[str, Any] = {
            "capability": resolved_capability,
            "model_profile": profile,
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

    def mark_generated(self, shot_id: str) -> dict[str, Any]:
        """draft|generated → generated (render / regenerate only)."""
        return self._transition(shot_id, allowed_from=("draft", "generated"), to="generated")

    def abandon(self, shot_id: str) -> dict[str, Any]:
        """draft|generated → abandoned (Discard). Terminal."""
        return self._transition(shot_id, allowed_from=("draft", "generated"), to="abandoned")

    def materialize_to_story(
        self,
        shot_id: str,
        *,
        project_id: str | None = None,
        generation_attempt_id: str | None = None,
    ) -> dict[str, Any]:
        """Copy generation state onto a Formal Story Shot — do not rerender.

        Transition: generated → adopted only.
        """
        pipe = self._c.shot_pipeline()
        scratch = pipe.get_shot(shot_id)
        meta = studio_meta(scratch.render_spec)
        if meta.get("source") != "quick_studio":
            raise ValueError("not a quick studio scratch shot")
        current = str(meta.get("lifecycle") or "draft")
        if current != "generated":
            raise ValueError(f"cannot materialize from lifecycle={current}; generate first")

        attempt_id = generation_attempt_id or self._latest_attempt_id(shot_id)
        if not attempt_id:
            raise ValueError("no generation to adopt; generate first")

        attempt = pipe.get_attempt(attempt_id)
        if not attempt.output_asset_ids:
            raise ValueError("generation has no output assets")

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

        copied_spec = deepcopy(scratch.render_spec)
        copied_spec.pop(_STUDIO_KEY, None)
        copied_spec["_adopted_from_scratch_shot_id"] = shot_id
        copied_spec["_adopted_generation_attempt_id"] = attempt_id
        formal = pipe.update_shot(formal.id, copied_spec)

        drafts = self._c.prompt_draft_service()
        drafts.ensure_for_shot(formal.id)
        snap_pos = attempt.payload.get("final_positive_prompt")
        snap_neg = attempt.payload.get("final_negative_prompt")
        if isinstance(snap_pos, str) and isinstance(snap_neg, str):
            drafts.update_edits(formal.id, snap_pos, snap_neg)

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
        if use_pose:
            patch["capability"] = "PoseControlledRender"
            stored = self._ensure_pose_asset(
                pose_id=pose_id,
                pose_view=pose_view,
                line=line,
                flipped=flipped,
            )
            if stored is None:
                raise ValueError("pose reference image unavailable")
            patch["pose_asset_uri"] = stored["uri"]
            # Provenance must describe the bytes actually sent to Comfy
            snap["pose_asset_sha256"] = stored["sha256"]
            snap["pose_asset_id"] = stored["asset_id"]
            snap["flipped"] = bool(flipped)
            patch["pose_provenance"] = snap
            patch["pose"]["line_sha256"] = stored["sha256"]
        else:
            patch["pose_asset_uri"] = None
        pipe = self._c.shot_pipeline()
        pipe.update_shot(shot_id, patch)
        drafts = self._c.prompt_draft_service()
        drafts.ensure_for_shot(shot_id)
        try:
            drafts.rebuild(shot_id, confirm=True)
        except ValueError:
            pass
        return self._session_view(shot_id)

    def _transition(
        self,
        shot_id: str,
        *,
        allowed_from: tuple[str, ...],
        to: ScratchLifecycle,
    ) -> dict[str, Any]:
        pipe = self._c.shot_pipeline()
        shot = pipe.get_shot(shot_id)
        meta = studio_meta(shot.render_spec)
        if meta.get("source") != "quick_studio":
            raise ValueError("not a quick studio scratch shot")
        current = str(meta.get("lifecycle") or "draft")
        if current not in allowed_from:
            raise ValueError(f"invalid lifecycle transition {current} → {to}")
        meta["lifecycle"] = to
        pipe.update_shot(shot_id, {_STUDIO_KEY: meta})
        return self._session_view(shot_id)

    def _ensure_pose_asset(
        self,
        *,
        pose_id: str,
        pose_view: str,
        line: dict[str, Any],
        flipped: bool,
    ) -> dict[str, str] | None:
        """Store Shisei line art (optionally H-flipped) for Comfy pose_image."""
        url = str(line.get("url") or "")
        marker = "/api/v1/references/assets/"
        rel = url.split(marker, 1)[-1] if marker in url else ""
        if not rel:
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
        out_mime = mime or "image/webp"
        suffix = "webp" if "webp" in out_mime else "png"
        if flipped:
            data, out_mime = _horizontal_flip(data)
            suffix = "png" if out_mime == "image/png" else suffix
        filename = f"{pose_id}-{pose_view}{'-flip' if flipped else ''}.{suffix}"
        stored = self._c.store_asset().execute(
            StoreBytesCommand(
                data=data,
                kind=AssetKind.REFERENCE,
                mime=out_mime,
                relative_dir="pose/shisei",
                filename=filename,
            )
        )
        return {
            "uri": stored.uri,
            "sha256": stored.sha256,
            "asset_id": str(stored.id),
        }

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
            "model_profile": shot.render_spec.get("model_profile", "anima"),
            "render_spec": shot.render_spec,
            "prompt_draft": draft,
            "pose_provenance": shot.render_spec.get("pose_provenance"),
        }

    def _latest_attempt_id(self, shot_id: str) -> str | None:
        pipe = self._c.shot_pipeline()
        history = pipe.list_attempts_for_shot(shot_id)
        for item in history:
            if item.get("status") == "succeeded" and item.get("output_asset_ids"):
                return str(item["id"])
        return None


def _horizontal_flip(data: bytes) -> tuple[bytes, str]:
    """Return PNG bytes of a horizontally flipped image + mime."""
    img = Image.open(io.BytesIO(data))
    flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    buf = io.BytesIO()
    # Prefer PNG for derived assets so hash is deterministic across codecs
    if flipped.mode not in ("RGB", "RGBA"):
        flipped = flipped.convert("RGBA")
    flipped.save(buf, format="PNG")
    return buf.getvalue(), "image/png"
