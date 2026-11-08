from __future__ import annotations

from typing import Any, Protocol


class LLMResponseError(RuntimeError):
    def __init__(self, reason: str, excerpt: str = "") -> None:
        self.reason = reason
        self.excerpt = excerpt[:500]
        super().__init__(f"{reason}: {self.excerpt}")


class LLMGateway(Protocol):
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str | None = None,
    ) -> dict[str, Any] | list[Any]: ...
