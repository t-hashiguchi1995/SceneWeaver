from __future__ import annotations

from typing import Any

from creator_studio.application.workflows.models import (
    WorkflowTemplate,
    WorkflowValidationError,
)


class WorkflowSlotValidator:
    """Validate template graph + slots before submit. Rejects unknown models."""

    def validate(
        self,
        template: WorkflowTemplate,
        *,
        approved_model_ids: set[str],
        model_id: str,
        slots: dict[str, Any] | None = None,
    ) -> None:
        errors: list[str] = []
        if model_id not in approved_model_ids:
            errors.append(f"unknown model rejected: {model_id}")
        if (
            template.required_model_id is not None
            and template.required_model_id != model_id
            and model_id not in approved_model_ids
        ):
            errors.append(
                f"model {model_id} does not match template requirement "
                f"{template.required_model_id}"
            )

        graph = template.workflow_graph
        for slot_name, binding in template.slots.items():
            node = graph.get(binding.node)
            if node is None:
                errors.append(f"missing node: {binding.node} (slot {slot_name})")
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                errors.append(f"node {binding.node} has no inputs dict")
                continue
            if binding.input not in inputs:
                errors.append(
                    f"wrong input: node {binding.node} missing '{binding.input}' "
                    f"(slot {slot_name})"
                )
                continue
            if slot_name == "seed":
                current = inputs[binding.input]
                if not isinstance(current, (int, float)) and current is not None:
                    errors.append(f"seed slot not patchable (type={type(current).__name__})")

        for _out_name, node_ids in template.outputs.items():
            for node_id in node_ids:
                if node_id not in graph:
                    errors.append(f"missing output node: {node_id}")

        if slots:
            for key in slots:
                if key not in template.slots and key not in {"candidate_count"}:
                    # candidate_count is Fake-backend meta, not a Comfy slot
                    pass

        if errors:
            raise WorkflowValidationError(errors)
