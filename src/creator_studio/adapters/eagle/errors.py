from __future__ import annotations

from enum import StrEnum


class EagleErrorCode(StrEnum):
    EAGLE_UNREACHABLE = "EAGLE_UNREACHABLE"
    EAGLE_DISABLED = "EAGLE_DISABLED"
    EAGLE_API_ERROR = "EAGLE_API_ERROR"
    EAGLE_PATH_UNCONVERTIBLE = "EAGLE_PATH_UNCONVERTIBLE"
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    ASSET_NOT_ADOPTED = "ASSET_NOT_ADOPTED"


class EagleError(RuntimeError):
    def __init__(self, code: EagleErrorCode, message: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {message}")
