from __future__ import annotations

import copy
import hashlib
import time
from pathlib import Path
from typing import Any

import httpx

from creator_studio.adapters.image.comfy_errors import (
    ComfyError,
    ComfyErrorCode,
    classify_comfy_message,
)
from creator_studio.application.workflows import WorkflowCompiler, WorkflowValidationError
from creator_studio.infrastructure.workflows.loader import WorkflowTemplateLoader
from creator_studio.infrastructure.workflows.registry_models import (
    load_approved_model_ids,
    resolve_template_id_for_capability,
)
from creator_studio.ports.asset_store import AssetStore
from creator_studio.ports.image_backend import (
    ExternalJobRef,
    GeneratedArtifact,
    JobProgress,
    RenderPlanDTO,
    ValidationResult,
)

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

_IMAGE_SLOT_KEYS = {"character_image", "garment_image", "pose_image", "image"}


class ComfyImageBackend:
    """Real ComfyUI ImageBackend. Same Port as FakeImageBackend."""

    def __init__(
        self,
        comfy_url: str,
        *,
        repo_root: Path | None = None,
        registry_path: Path | None = None,
        asset_store: AssetStore | None = None,
        dry_run: bool = False,
        timeout: float = 30.0,
        poll_timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self._url = comfy_url.rstrip("/")
        self._loader = WorkflowTemplateLoader(repo_root)
        self._compiler = WorkflowCompiler()
        self._registry_path = registry_path
        self._store = asset_store
        self._dry_run = dry_run
        self._timeout = timeout
        self._poll_timeout = poll_timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._jobs: dict[str, dict[str, Any]] = {}

    def capabilities(self) -> set[str]:
        return {
            "BaseRender",
            "PoseControlledRender",
            "LayoutGuidedRender",
            "OutfitTryOn",
            "ExpressionEdit",
            "ImageEdit",
        }

    def health(self) -> bool:
        try:
            timeout = min(8.0, max(self._timeout, 5.0))
            response = httpx.get(f"{self._url}/system_stats", timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    def validate(self, plan: RenderPlanDTO) -> ValidationResult:
        try:
            self._compile(plan)
        except WorkflowValidationError as exc:
            return ValidationResult(ok=False, errors=[f"WORKFLOW_INVALID: {e}" for e in exc.errors])
        except ComfyError as exc:
            return ValidationResult(ok=False, errors=[str(exc)])
        except (FileNotFoundError, ValueError, KeyError) as exc:
            return ValidationResult(ok=False, errors=[str(exc)])
        return ValidationResult(ok=True)

    def submit(self, plan: RenderPlanDTO) -> ExternalJobRef:
        compiled = self._compile(plan)
        if self._dry_run:
            ref = f"comfy-dry-{compiled.workflow_hash[:16]}"
            self._jobs[ref] = {
                "compiled": compiled,
                "plan": plan,
                "mode": "dry_run",
                "model_id": compiled.model_id,
            }
            return ExternalJobRef(ref=ref, provider="comfyui")

        if not self.health():
            raise ComfyError(ComfyErrorCode.COMFY_UNREACHABLE, f"no response from {self._url}")

        graph = self._materialize_image_slots(compiled.graph, plan)
        payload = {"prompt": graph, "client_id": "sceneweaver"}
        try:
            response = httpx.post(
                f"{self._url}/prompt",
                json=payload,
                timeout=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001
            raise ComfyError(
                ComfyErrorCode.COMFY_UNREACHABLE,
                f"submit connection failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            detail = response.text[:500]
            code = classify_comfy_message(detail)
            if code == ComfyErrorCode.GENERATION_FAILED:
                code = ComfyErrorCode.SUBMIT_FAILED
            raise ComfyError(code, detail)

        data = response.json()
        if data.get("node_errors"):
            detail = str(data["node_errors"])
            raise ComfyError(classify_comfy_message(detail), detail)

        prompt_id = str(data.get("prompt_id") or data.get("promptId") or "")
        if not prompt_id:
            raise ComfyError(ComfyErrorCode.SUBMIT_FAILED, "Comfy /prompt returned no prompt_id")

        self._jobs[prompt_id] = {
            "compiled": compiled,
            "plan": plan,
            "mode": "live",
            "model_id": compiled.model_id,
            "graph": graph,
        }
        return ExternalJobRef(ref=prompt_id, provider="comfyui")

    def poll(self, ref: ExternalJobRef) -> JobProgress:
        job = self._jobs.get(ref.ref)
        if job is None:
            return JobProgress(status="failed", message="unknown job")
        if job["mode"] == "dry_run":
            return JobProgress(status="succeeded", percent=100.0, message="comfy dry-run")
        try:
            response = httpx.get(f"{self._url}/history/{ref.ref}", timeout=self._timeout)
        except Exception as exc:  # noqa: BLE001
            return JobProgress(status="failed", message=f"COMFY_UNREACHABLE: {exc}")
        if response.status_code != 200:
            return JobProgress(status="running", percent=10.0, message="waiting")
        history = response.json() or {}
        entry = history.get(ref.ref)
        if not entry:
            return JobProgress(status="running", percent=40.0, message="queued")
        status_obj = entry.get("status") or {}
        if status_obj.get("status_str") == "error" or status_obj.get("completed") is False:
            messages = status_obj.get("messages") or []
            detail = str(messages) if messages else "generation error"
            return JobProgress(
                status="failed",
                message=f"{classify_comfy_message(detail).value}: {detail}",
            )
        outputs = entry.get("outputs") or {}
        if outputs:
            job["history"] = entry
            return JobProgress(status="succeeded", percent=100.0, message="comfy done")
        return JobProgress(status="running", percent=70.0, message="rendering")

    def wait(self, ref: ExternalJobRef) -> JobProgress:
        """Poll until terminal state or timeout (live smoke)."""
        deadline = time.time() + self._poll_timeout
        last = JobProgress(status="queued", message="waiting")
        while time.time() < deadline:
            last = self.poll(ref)
            if last.status in {"succeeded", "failed", "cancelled"}:
                if last.status == "failed":
                    code = classify_comfy_message(last.message)
                    raise ComfyError(code, last.message)
                return last
            time.sleep(self._poll_interval)
        raise ComfyError(
            ComfyErrorCode.TIMEOUT,
            f"job {ref.ref} exceeded {self._poll_timeout:.0f}s",
        )

    def collect(self, ref: ExternalJobRef) -> list[GeneratedArtifact]:
        job = self._jobs.get(ref.ref)
        if job is None:
            return []
        plan: RenderPlanDTO = job["plan"]
        compiled = job["compiled"]
        default_count = 1 if job["mode"] == "live" else 4
        count = int(plan.slots.get("candidate_count", default_count))
        if job["mode"] == "dry_run":
            return [
                GeneratedArtifact(
                    bytes_data=_PNG
                    + f"comfy-dry-{compiled.template_id}-{i}".encode()
                    + hashlib.sha256(str(compiled.seed + i).encode()).digest()[:4],
                    mime="image/png",
                    metadata=self._artifact_metadata(compiled, plan, ref, index=i),
                )
                for i in range(count)
            ]

        history = job.get("history")
        if not history:
            progress = self.poll(ref)
            if progress.status != "succeeded":
                raise ComfyError(ComfyErrorCode.OUTPUT_NOT_FOUND, progress.message)
            history = job.get("history")
        if not history:
            raise ComfyError(ComfyErrorCode.OUTPUT_NOT_FOUND, f"no history for {ref.ref}")

        images = self._extract_images(history)
        if not images:
            raise ComfyError(ComfyErrorCode.OUTPUT_NOT_FOUND, f"no image outputs for {ref.ref}")

        artifacts: list[GeneratedArtifact] = []
        for i, image_info in enumerate(images[:count]):
            data = self._download_image(image_info)
            if not data:
                raise ComfyError(ComfyErrorCode.OUTPUT_NOT_FOUND, f"empty image bytes for {image_info}")
            artifacts.append(
                GeneratedArtifact(
                    bytes_data=data,
                    mime="image/png",
                    metadata=self._artifact_metadata(
                        compiled, plan, ref, index=i, filename=image_info.get("filename")
                    ),
                )
            )
        return artifacts

    def cancel(self, ref: ExternalJobRef) -> None:
        self._jobs.pop(ref.ref, None)

    def _compile(self, plan: RenderPlanDTO):
        approved = load_approved_model_ids(self._registry_path)
        model_id, template_path = resolve_template_id_for_capability(
            plan.capability, self._registry_path
        )
        if plan.template_id:
            template = self._loader.load(plan.template_id)
        else:
            template = self._loader.load_relative(template_path)
        if template.capability != plan.capability:
            raise ComfyError(
                ComfyErrorCode.WORKFLOW_INVALID,
                f"template capability mismatch: {template.capability} != {plan.capability}",
            )
        try:
            return self._compiler.compile(
                template,
                slots=plan.slots,
                seed=plan.seed,
                model_id=model_id,
                approved_model_ids=approved,
            )
        except WorkflowValidationError as exc:
            raise ComfyError(ComfyErrorCode.WORKFLOW_INVALID, "; ".join(exc.errors)) from exc

    @staticmethod
    def _artifact_metadata(
        compiled: Any,
        plan: RenderPlanDTO,
        ref: ExternalJobRef,
        *,
        index: int,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "seed": compiled.seed,
            "index": index,
            "template_id": compiled.template_id,
            "workflow_template_id": compiled.template_id,
            "workflow_hash": compiled.workflow_hash,
            "capability": plan.capability,
            "provider": "comfyui",
            "model_id": compiled.model_id,
            "external_job_ref": ref.ref,
            **extra,
        }

    def _materialize_image_slots(self, graph: dict[str, Any], plan: RenderPlanDTO) -> dict[str, Any]:
        """Upload asset:// images so LoadImage nodes receive Comfy filenames."""
        out = copy.deepcopy(graph)
        for slot_name, value in plan.slots.items():
            if slot_name not in _IMAGE_SLOT_KEYS:
                continue
            if not isinstance(value, str) or not value.startswith("asset://"):
                continue
            filename = self._upload_asset_uri(value)
            for node in out.values():
                inputs = node.get("inputs") or {}
                for key, cur in inputs.items():
                    if cur == value:
                        inputs[key] = filename
        return out

    def _upload_asset_uri(self, uri: str) -> str:
        if self._store is None:
            raise ComfyError(ComfyErrorCode.SUBMIT_FAILED, "asset_store required for image upload")
        path = self._store.path_for_uri(uri)
        data = path.read_bytes()
        files = {"image": (path.name, data, "image/png")}
        try:
            response = httpx.post(
                f"{self._url}/upload/image",
                files=files,
                timeout=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001
            raise ComfyError(ComfyErrorCode.COMFY_UNREACHABLE, f"upload failed: {exc}") from exc
        if response.status_code >= 400:
            raise ComfyError(ComfyErrorCode.SUBMIT_FAILED, response.text[:300])
        payload = response.json()
        name = payload.get("name") or payload.get("filename")
        if not name:
            raise ComfyError(ComfyErrorCode.SUBMIT_FAILED, f"upload missing name: {payload}")
        return str(name)

    def _extract_images(self, history_entry: dict[str, Any]) -> list[dict[str, Any]]:
        images: list[dict[str, Any]] = []
        outputs = history_entry.get("outputs") or {}
        for node_out in outputs.values():
            for img in node_out.get("images") or []:
                images.append(img)
        return images

    def _download_image(self, image_info: dict[str, Any]) -> bytes:
        params = {
            "filename": image_info.get("filename"),
            "subfolder": image_info.get("subfolder") or "",
            "type": image_info.get("type") or "output",
        }
        try:
            response = httpx.get(f"{self._url}/view", params=params, timeout=self._timeout)
        except Exception as exc:  # noqa: BLE001
            raise ComfyError(ComfyErrorCode.COMFY_UNREACHABLE, f"view failed: {exc}") from exc
        if response.status_code >= 400 or not response.content:
            raise ComfyError(
                ComfyErrorCode.OUTPUT_NOT_FOUND,
                f"view HTTP {response.status_code} for {params}",
            )
        return response.content
