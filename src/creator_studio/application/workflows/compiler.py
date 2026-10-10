from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from creator_studio.application.workflows.models import (
    CompiledWorkflow,
    WorkflowTemplate,
)
from creator_studio.application.workflows.validator import WorkflowSlotValidator


class WorkflowCompiler:
    def __init__(self, validator: WorkflowSlotValidator | None = None) -> None:
        self._validator = validator or WorkflowSlotValidator()

    def compile(
        self,
        template: WorkflowTemplate,
        *,
        slots: dict[str, Any],
        seed: int,
        model_id: str,
        approved_model_ids: set[str],
    ) -> CompiledWorkflow:
        self._validator.validate(
            template,
            approved_model_ids=approved_model_ids,
            model_id=model_id,
            slots=slots,
        )
        graph = copy.deepcopy(template.workflow_graph)
        applied: dict[str, Any] = {}
        for slot_name, binding in template.slots.items():
            if slot_name == "seed":
                value: Any = seed
            elif slot_name in slots:
                value = slots[slot_name]
            else:
                continue
            graph[binding.node]["inputs"][binding.input] = value
            applied[slot_name] = value

        payload = {
            "template_id": template.id,
            "capability": template.capability,
            "model_id": model_id,
            "seed": seed,
            "graph": graph,
        }
        workflow_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        return CompiledWorkflow(
            template_id=template.id,
            capability=template.capability,
            graph=graph,
            workflow_hash=workflow_hash,
            seed=seed,
            model_id=model_id,
            slots_applied=applied,
        )
