from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from creator_studio.application.workflows.models import SlotBinding, WorkflowTemplate
from creator_studio.infrastructure.settings.config import REPO_ROOT


class WorkflowTemplateLoader:
    """Load SceneWeaver-native template YAML + Comfy API JSON from disk."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or REPO_ROOT
        self._by_id: dict[str, Path] | None = None

    def _index(self) -> dict[str, Path]:
        if self._by_id is not None:
            return self._by_id
        index: dict[str, Path] = {}
        for path in (self._root / "workflows" / "comfy").glob("*.template.yaml"):
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            tid = str(data.get("id", ""))
            if tid:
                index[tid] = path
        self._by_id = index
        return index

    def list_ids(self) -> list[str]:
        return sorted(self._index())

    def load(self, template_id: str) -> WorkflowTemplate:
        path = self._index().get(template_id)
        if path is None:
            raise FileNotFoundError(f"workflow template not found: {template_id}")
        return self.load_path(path)

    def load_relative(self, relative_path: str) -> WorkflowTemplate:
        return self.load_path(self._root / relative_path)

    def load_path(self, path: Path) -> WorkflowTemplate:
        with path.open(encoding="utf-8") as f:
            meta: dict[str, Any] = yaml.safe_load(f) or {}
        workflow_rel = str(meta["workflow_file"])
        graph_path = self._root / workflow_rel
        with graph_path.open(encoding="utf-8") as f:
            import json

            graph = json.load(f)
        slots_raw = meta.get("slots") or {}
        slots = {
            name: SlotBinding(node=str(spec["node"]), input=str(spec["input"]))
            for name, spec in slots_raw.items()
        }
        return WorkflowTemplate(
            id=str(meta["id"]),
            backend=str(meta.get("backend", "comfyui")),
            capability=str(meta["capability"]),
            workflow_file=workflow_rel,
            slots=slots,
            outputs=dict(meta.get("outputs") or {}),
            workflow_graph=graph,
            required_model_id=meta.get("required_model_id"),
        )
