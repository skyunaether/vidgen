"""SSE log streaming route."""
from __future__ import annotations

import json

from litestar import get
from litestar.exceptions import NotFoundException
from litestar.response import ServerSentEvent, ServerSentEventMessage

from webui.backend.job_manager import job_manager


@get("/api/jobs/{job_id:str}/stream", media_type="text/event-stream")
async def stream_job(job_id: str) -> ServerSentEvent:
    if job_manager.status(job_id) is None:
        raise NotFoundException(f"Job {job_id!r} not found")

    async def _generate():
        async for msg in job_manager.stream(job_id):
            yield ServerSentEventMessage(data=json.dumps(msg))

    return ServerSentEvent(_generate())
