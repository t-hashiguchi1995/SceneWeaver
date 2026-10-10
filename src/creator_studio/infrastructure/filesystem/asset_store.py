from __future__ import annotations

import hashlib
from pathlib import Path

from creator_studio.ports.asset_store import StoredBlob


class FilesystemAssetStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, data: bytes, *, relative_dir: str, filename: str) -> StoredBlob:
        digest = hashlib.sha256(data).hexdigest()
        dest_dir = self._root / relative_dir / digest[:2]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{digest}_{filename}"
        if not dest.exists():
            dest.write_bytes(data)
        uri = f"asset://{digest}/{filename}"
        return StoredBlob(sha256=digest, path=dest, byte_size=len(data), uri=uri)

    def path_for_uri(self, uri: str) -> Path:
        # asset://{sha256}/{filename}
        if not uri.startswith("asset://"):
            raise ValueError(f"unsupported uri: {uri}")
        rest = uri.removeprefix("asset://")
        sha256, _, filename = rest.partition("/")
        path = self._root / sha256[:2] / f"{sha256}_{filename}"
        # also search under relative dirs
        if path.exists():
            return path
        for candidate in self._root.rglob(f"{sha256}_{filename}"):
            return candidate
        raise FileNotFoundError(uri)