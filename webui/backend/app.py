"""Litestar ASGI application — VidGen Web API."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.static_files import create_static_files_router
from litestar.logging import LoggingConfig

# Ensure the repo root is on sys.path so `vidgen` can be imported
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from webui.backend.job_manager import job_manager
from webui.backend.routes.config import get_config, save_config
from webui.backend.routes.jobs import create_job, get_job, cancel_job
from webui.backend.routes.stream import stream_job
from webui.backend.routes.outputs import list_outputs, download_output

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


def _on_startup() -> None:
    """Capture the running event loop for thread-safe queue operations."""
    loop = asyncio.get_event_loop()
    job_manager.set_event_loop(loop)


app = Litestar(
    route_handlers=[
        get_config,
        save_config,
        create_job,
        get_job,
        cancel_job,
        stream_job,
        list_outputs,
        download_output,
    ],
    cors_config=CORSConfig(
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    ),
    on_startup=[_on_startup],
    logging_config=LoggingConfig(
        loggers={
            "vidgen": {"level": "INFO", "handlers": ["queue_listener"]},
            "webui": {"level": "INFO", "handlers": ["queue_listener"]},
        }
    ),
)

# Serve built frontend (production). During dev, Vite dev server handles this.
if FRONTEND_DIST.exists():
    app.register(
        create_static_files_router(
            path="/",
            directories=[FRONTEND_DIST],
            html_mode=True,
        )
    )
