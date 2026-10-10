from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SlotBinding:
    node: str
    input: str


@dataclass
class WorkflowTemplate:
    id: str
    backend: str
    capability: str
    workflow_file: str
    slots: dict[str, SlotBinding]
    outputs: dict[str, list[str]]
    workflow_graph: dict[str, Any]
    required_model_id: str | None = None


@dataclass
class CompiledWorkflow:
    template_id: str
    capability: str
    graph: dict[str, Any]
    workflow_hash: str
    seed: int
    model_id: str
    slots_applied: dict[str, Any] = field(default_factory=dict)


class WorkflowValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        ValueError.__init__(self, "; ".join(self.errors))
