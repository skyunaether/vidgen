"""
VidGen Web UI launcher.

Usage:
  python webui/start.py             # Production (serves built frontend)
  python webui/start.py --dev       # Dev mode (frontend on :5173, backend on :8000)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
FRONTEND_DIR = Path(__file__).parent / "frontend"


def main() -> None:
    dev = "--dev" in sys.argv

    print("=" * 60)
    print("  VidGen Web UI")
    print("=" * 60)

    # Backend
    print(f"\n► Starting backend on http://localhost:{BACKEND_PORT} …")
    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "webui.backend.app:app",
        "--port", str(BACKEND_PORT),
        "--host", "0.0.0.0",
    ]
    if dev:
        backend_cmd.append("--reload")

    backend = subprocess.Popen(
        backend_cmd,
        cwd=str(REPO_ROOT),
    )

    if dev:
        # Frontend dev server
        print(f"► Starting Vite dev server on http://localhost:{FRONTEND_PORT} …")
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend = subprocess.Popen(
            [npm, "run", "dev"],
            cwd=str(FRONTEND_DIR),
        )
        time.sleep(2.5)
        url = f"http://localhost:{FRONTEND_PORT}"
    else:
        frontend = None
        time.sleep(1.5)
        url = f"http://localhost:{BACKEND_PORT}"

    print(f"\n✅ Opening {url}")
    webbrowser.open(url)

    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\n⛔ Shutting down…")
    finally:
        backend.terminate()
        if frontend:
            frontend.terminate()


if __name__ == "__main__":
    main()
