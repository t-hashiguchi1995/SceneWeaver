from __future__ import annotations

from typing import Any, Protocol


class LLMGateway(Protocol):
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str | None = None,
    ) -> dict[str, Any] | list[Any]: ...