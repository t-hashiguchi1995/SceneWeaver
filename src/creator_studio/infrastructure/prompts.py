from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from creator_studio.infrastructure.settings.config import REPO_ROOT


class PromptRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (REPO_ROOT / "prompts")
        self._env = Environment(
            loader=FileSystemLoader(str(self._root)),
            undefined=StrictUndefined,
            autoescape=False,
        )

    def render(self, relative_path: str, **kwargs: object) -> str:
        return self._env.get_template(relative_path).render(**kwargs)