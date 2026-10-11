from __future__ import annotations

from creator_studio.ports.image_backend import (
    ExternalJobRef,
    GeneratedArtifact,
    ImageBackend,
    RenderPlanDTO,
)


def submit_wait_collect(
    image: ImageBackend,
    plan: RenderPlanDTO,
) -> tuple[ExternalJobRef, list[GeneratedArtifact]]:
    """Shared ImageBackend path used by TryOn / Shot UseCases."""
    ref = image.submit(plan)
    wait = getattr(image, "wait", None)
    if callable(wait):
        wait(ref)
    else:
        progress = image.poll(ref)
        if progress.status != "succeeded":
            raise RuntimeError(progress.message or "generation failed")

    artifacts = image.collect(ref)
    if not artifacts:
        raise RuntimeError("OUTPUT_NOT_FOUND: no artifacts collected")
    return ref, artifacts


def candidate_count_for_backend(image: ImageBackend) -> int:
    """Creator review presents four candidates on all image backends."""
    return 4


__all__ = ["candidate_count_for_backend", "submit_wait_collect"]
