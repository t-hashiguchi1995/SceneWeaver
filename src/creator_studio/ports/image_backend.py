from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ExternalJobRef:
    ref: str
    provider: str


@dataclass
class JobProgress:
    status: str
    percent: float = 0.0
    message: str = ""


@dataclass
class GeneratedArtifact:
    bytes_data: bytes
    mime: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderPlanDTO:
    capability: str
    template_id: str
    seed: int
    slots: dict[str, Any]
    refs: dict[str, str] = field(default_factory=dict)


class ImageBackend(Protocol):
    def capabilities(self) -> set[str]: ...

    def validate(self, plan: RenderPlanDTO) -> ValidationResult: ...

    def submit(self, plan: RenderPlanDTO) -> ExternalJobRef: ...

    def poll(self, ref: ExternalJobRef) -> JobProgress: ...

    def collect(self, ref: ExternalJobRef) -> list[GeneratedArtifact]: ...

    def cancel(self, ref: ExternalJobRef) -> None: ...