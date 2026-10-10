from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderHealth:
    available: bool
    detail: str = ""


class RuntimeCapabilityProbe(Protocol):
    """Port so Application never talks to HTTP/runtime URLs directly."""

    def probe(self) -> ProviderHealth: ...
