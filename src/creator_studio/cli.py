from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def _ensure_repo_on_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def run_api() -> None:
    _ensure_repo_on_path()
    from apps.api.main import run

    run()


def run_worker() -> None:
    _ensure_repo_on_path()
    from apps.worker.main import run

    run()


def run_start() -> None:
    """Launch API + Worker + Web and open the browser (Application Shell)."""
    root = _ensure_repo_on_path()
    from creator_studio.infrastructure.settings import get_settings

    settings = get_settings()
    api_port = settings.port
    web_port = int(os.environ.get("SCENEWEAVER_WEB_PORT", "5173"))
    host = settings.host
    procs: list[subprocess.Popen[bytes]] = []

    def stop(_signum: int | None = None, _frame: object | None = None) -> None:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    env = os.environ.copy()
    env.setdefault("SCENEWEAVER_CORS_ORIGINS", f"http://{host}:{web_port},http://127.0.0.1:{web_port}")
    env["SCENEWEAVER_API_PROXY"] = f"http://{host}:{api_port}"
    env["SCENEWEAVER_WEB_PORT"] = str(web_port)

    print(f"[sceneweaver] starting API on http://{host}:{api_port}")
    procs.append(
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", host, "--port", str(api_port)],
            cwd=str(root),
            env=env,
        )
    )
    print("[sceneweaver] starting Worker")
    procs.append(
        subprocess.Popen(
            [sys.executable, "-c", "from creator_studio.cli import run_worker; run_worker()"],
            cwd=str(root),
            env=env,
        )
    )
    web_dir = root / "apps" / "web"
    print(f"[sceneweaver] starting Web on http://{host}:{web_port}")
    procs.append(
        subprocess.Popen(
            ["pnpm", "exec", "vite", "--host", host, "--port", str(web_port)],
            cwd=str(web_dir),
            env=env,
        )
    )

    import urllib.request

    url = f"http://{host}:{web_port}/"
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://{host}:{api_port}/health", timeout=1)
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        print("[sceneweaver] services did not become healthy in time", file=sys.stderr)
        stop()

    print(f"[sceneweaver] opening {url}")
    webbrowser.open(url)
    print("[sceneweaver] running — Ctrl+C to stop")
    while True:
        for proc in procs:
            code = proc.poll()
            if code is not None:
                print(f"[sceneweaver] process exited ({code})", file=sys.stderr)
                stop()
        time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="sceneweaver")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("start", help="Start API + Worker + Web and open browser")
    sub.add_parser("api", help="Run API only")
    sub.add_parser("worker", help="Run Worker only")
    args = parser.parse_args()
    if args.cmd == "start":
        run_start()
    elif args.cmd == "api":
        run_api()
    elif args.cmd == "worker":
        run_worker()
    else:
        parser.print_help()
        raise SystemExit(2)


if __name__ == "__main__":
    main()
