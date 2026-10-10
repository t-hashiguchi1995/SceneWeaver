from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StoredBlob:
    sha256: str
    path: Path
    byte_size: int
    uri: str


class AssetStore(Protocol):
    def put_bytes(self, data: bytes, *, relative_dir: str, filename: str) -> StoredBlob: ...

    def path_for_uri(self, uri: str) -> Path: ...