from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def run_api() -> None:
    _ensure_repo_on_path()
    from apps.api.main import run

    run()


def run_worker() -> None:
    _ensure_repo_on_path()
    from apps.worker.main import run

    run()