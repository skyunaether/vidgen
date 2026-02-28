"""Job submit / status / cancel routes."""
from __future__ import annotations

from litestar import get, post
from litestar.exceptions import NotFoundException

from webui.backend.job_manager import job_manager
from webui.backend.models import ExecuteRequest, JobStatus


@post("/api/jobs")
async def create_job(data: ExecuteRequest) -> dict:
    job_id = job_manager.submit(data)
    return {"job_id": job_id}


@get("/api/jobs/{job_id:str}")
async def get_job(job_id: str) -> JobStatus:
    status = job_manager.status(job_id)
    if status is None:
        raise NotFoundException(f"Job {job_id!r} not found")
    return status


@post("/api/jobs/{job_id:str}/cancel")
async def cancel_job(job_id: str) -> dict:
    job_manager.cancel(job_id)
    return {"ok": True, "job_id": job_id}
