from __future__ import annotations

import hashlib
import time
from pathlib import Path

from creator_studio.application.workflows import WorkflowCompiler, WorkflowValidationError
from creator_studio.infrastructure.settings.config import REPO_ROOT
from creator_studio.infrastructure.workflows.loader import WorkflowTemplateLoader
from creator_studio.infrastructure.workflows.registry_models import (
    load_approved_model_ids,
    resolve_template_id_for_capability,
)
from creator_studio.ports.image_backend import (
    ExternalJobRef,
    GeneratedArtifact,
    JobProgress,
    RenderPlanDTO,
    ValidationResult,
)

_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xc8]u\x14\x00\x03d\x01\xdd\xd6\x1ef\x99\x00\x00\x00\x00IEND\xaeB`\x82'

_LABELS = ("a", "b", "c", "d")


class FakeImageBackend:
    """GPU-free ImageBackend. Shares WorkflowCompiler validation with Comfy adapter."""

    def __init__(
        self,
        *,
        delay_ms: int = 200,
        fixture_root: Path | None = None,
        repo_root: Path | None = None,
        registry_path: Path | None = None,
        use_workflow_compiler: bool = True,
    ) -> None:
        self._jobs: dict[str, RenderPlanDTO] = {}
        self._delay_ms = delay_ms
        self._fixture_root = fixture_root or (REPO_ROOT / "tests" / "fixtures" / "generated")
        self._loader = WorkflowTemplateLoader(repo_root)
        self._compiler = WorkflowCompiler()
        self._registry_path = registry_path
        self._use_workflow_compiler = use_workflow_compiler

    def capabilities(self) -> set[str]:
        return {
            "BaseRender",
            "PoseControlledRender",
            "OutfitTryOn",
            "ExpressionEdit",
            "ImageEdit",
        }

    def validate(self, plan: RenderPlanDTO) -> ValidationResult:
        if plan.capability not in self.capabilities():
            return ValidationResult(ok=False, errors=[f"unsupported capability: {plan.capability}"])
        if self._use_workflow_compiler and plan.template_id:
            try:
                approved = load_approved_model_ids(self._registry_path)
                model_id, _ = resolve_template_id_for_capability(
                    plan.capability, self._registry_path
                )
                template = self._loader.load(plan.template_id)
                self._compiler.compile(
                    template,
                    slots=plan.slots,
                    seed=plan.seed,
                    model_id=model_id,
                    approved_model_ids=approved,
                )
            except WorkflowValidationError as exc:
                return ValidationResult(ok=False, errors=list(exc.errors))
            except (FileNotFoundError, ValueError, KeyError) as exc:
                return ValidationResult(ok=False, errors=[str(exc)])
            return ValidationResult(ok=True)
        if "positive_prompt" not in plan.slots and plan.capability != "OutfitTryOn":
            if "edit_prompt" not in plan.slots:
                return ValidationResult(ok=False, errors=["missing prompt slot"])
        return ValidationResult(ok=True)

    def submit(self, plan: RenderPlanDTO) -> ExternalJobRef:
        ref = f"fake-{hashlib.sha256(repr(plan).encode()).hexdigest()[:16]}"
        self._jobs[ref] = plan
        return ExternalJobRef(ref=ref, provider="fake")

    def poll(self, ref: ExternalJobRef) -> JobProgress:
        if ref.ref not in self._jobs:
            return JobProgress(status="failed", message="unknown job")
        if self._delay_ms > 0:
            time.sleep(self._delay_ms / 1000.0)
        return JobProgress(status="succeeded", percent=100.0, message="fake done")

    def wait(self, ref: ExternalJobRef) -> JobProgress:
        return self.poll(ref)

    def collect(self, ref: ExternalJobRef) -> list[GeneratedArtifact]:
        plan = self._jobs.get(ref.ref)
        if plan is None:
            return []
        count = int(plan.slots.get("candidate_count", 4))
        prefix = "tryon" if plan.capability == "OutfitTryOn" else "anima"
        artifacts: list[GeneratedArtifact] = []
        for i in range(count):
            label = _LABELS[i] if i < len(_LABELS) else str(i)
            data = self._load_candidate(prefix, label, plan.seed, i, plan.capability)
            artifacts.append(
                GeneratedArtifact(
                    bytes_data=data,
                    mime="image/png",
                    metadata={
                        "seed": plan.seed,
                        "index": i,
                        "label": label.upper(),
                        "capability": plan.capability,
                        "provider": "fake",
                        "workflow_template_id": plan.template_id,
                        "workflow_hash": hashlib.sha256(
                            f"fake:{plan.template_id}:{plan.seed}".encode()
                        ).hexdigest(),
                        "external_job_ref": ref.ref,
                    },
                )
            )
        return artifacts

    def cancel(self, ref: ExternalJobRef) -> None:
        self._jobs.pop(ref.ref, None)

    def _load_candidate(
        self, prefix: str, label: str, seed: int, index: int, capability: str
    ) -> bytes:
        path = self._fixture_root / f"{prefix}_{label}.png"
        if path.exists():
            return path.read_bytes() + f"#{seed}:{index}:{capability}".encode()
        self._fixture_root.mkdir(parents=True, exist_ok=True)
        base = _PNG + f"{prefix}-{label}".encode()
        path.write_bytes(base)
        return base + f"#{seed}:{index}:{capability}".encode()
