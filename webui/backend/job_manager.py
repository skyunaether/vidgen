"""Job lifecycle management: submit, cancel, poll, SSE streaming."""
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import AsyncIterator

from .models import ExecuteRequest, JobStatus

log = logging.getLogger(__name__)

# Root of the vidgen repo (two levels up from this file)
REPO_ROOT = Path(__file__).parent.parent.parent


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._queues: dict[str, asyncio.Queue] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, request: ExecuteRequest) -> str:
        """Start a job in a background thread. Returns the job_id immediately."""
        job_id = str(uuid.uuid4())[:8]
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[job_id] = queue
        self._jobs[job_id] = {
            "state": "queued",
            "started_at": None,
            "finished_at": None,
            "output": None,
            "error": None,
            "_pipeline": None,
        }

        loop = self._loop or asyncio.get_event_loop()

        def _push(msg: dict) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, msg)

        def _progress(text: str) -> None:
            _push({"type": "log", "text": text, "ts": time.time()})

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, request, _progress, _push),
            daemon=True,
        )
        thread.start()
        return job_id

    def cancel(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        pipeline = job.get("_pipeline")
        if pipeline is not None:
            pipeline.cancel()
        job["state"] = "cancelled"

    def status(self, job_id: str) -> JobStatus | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return JobStatus(
            job_id=job_id,
            state=job["state"],
            started_at=job["started_at"],
            finished_at=job["finished_at"],
            output_path=job["output"],
            error=job["error"],
        )

    async def stream(self, job_id: str) -> AsyncIterator[dict]:
        """Async generator — yields SSE message dicts until job completes."""
        queue = self._queues.get(job_id)
        if queue is None:
            return
        while True:
            msg = await queue.get()
            yield msg
            if msg.get("type") == "status":
                break

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_job(
        self,
        job_id: str,
        request: ExecuteRequest,
        progress_cb,
        push_raw,
    ) -> None:
        job = self._jobs[job_id]
        job["state"] = "running"
        job["started_at"] = time.time()
        try:
            if request.multi_agent.enabled:
                output = self._run_orchestrator(request, progress_cb)
            else:
                output = self._run_pipeline(job_id, job, request, progress_cb)

            job["state"] = "done"
            job["output"] = str(output) if output else None
            job["finished_at"] = time.time()
            push_raw({"type": "status", "state": "done", "output": job["output"]})

        except Exception as exc:
            log.exception("Job %s failed", job_id)
            job["state"] = "failed"
            job["error"] = str(exc)
            job["finished_at"] = time.time()
            push_raw({"type": "status", "state": "failed", "error": str(exc)})

    def _run_pipeline(self, job_id: str, job: dict, request: ExecuteRequest, progress_cb) -> Path | None:
        """Run the vidgen Pipeline directly (non-multi-agent mode)."""
        # Late import to avoid circular deps and keep startup fast
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from vidgen.config import Config
        from vidgen.pipeline import Pipeline, PipelineOptions as EngineOptions
        from vidgen.scriptgen import parse_user_story, parse_markdown_story
        from vidgen.batchutil import resolve_md_paths as resolve_paths

        config = Config.load()
        if request.use_ai_music is not None:
            config.use_ai_music = request.use_ai_music
        if request.use_ai_tts is not None:
            config.use_ai_tts = request.use_ai_tts

        opts = EngineOptions(**request.pipeline.model_dump())
        pipeline = Pipeline(
            config,
            progress_cb=progress_cb,
            use_placeholders=request.use_test_mode,
            options=opts,
        )
        job["_pipeline"] = pipeline

        if request.mode == "auto":
            return pipeline.run(request.prompt)

        elif request.mode == "manual":
            from vidgen.scriptgen import StorySettings
            scenes, settings = _parse_manual(request.story)
            if not scenes:
                raise ValueError("Manual mode: no scenes parsed from story input.")
            pipeline.inject_scenes(scenes, settings)
            return pipeline.run(request.story)

        elif request.mode == "files":
            paths = resolve_paths(request.files_path)
            if not paths:
                raise ValueError(f"No markdown files found at: {request.files_path}")
            last_output = None
            for p in paths:
                text = Path(p).read_text(encoding="utf-8")
                title, scenes, settings = parse_markdown_story(text)
                pipeline2 = Pipeline(
                    config,
                    progress_cb=progress_cb,
                    use_placeholders=request.use_test_mode,
                    options=opts,
                )
                job["_pipeline"] = pipeline2
                pipeline2.inject_scenes(scenes, settings)
                last_output = pipeline2.run(title or text[:80])
            return last_output

        raise ValueError(f"Unknown mode: {request.mode}")

    def _run_orchestrator(self, request: ExecuteRequest, progress_cb) -> Path | None:
        """Run orchestrator.py as a subprocess, streaming its stdout as log lines."""
        cmd = [
            sys.executable,
            str(REPO_ROOT / "orchestrator.py"),
            "--prompt", request.prompt or request.story,
            "--max-iterations", str(request.multi_agent.max_iterations),
        ]
        progress_cb(f"  [multi-agent] Running: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(REPO_ROOT),
        )
        output_path: str | None = None
        for line in proc.stdout:
            line = line.rstrip()
            progress_cb(line)
            if "Video saved to:" in line or "vidgen_" in line and ".mp4" in line:
                import re
                m = re.search(r'(output[/\\][^\s]+\.mp4)', line)
                if m:
                    output_path = str(REPO_ROOT / m.group(1))
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Orchestrator exited with code {proc.returncode}")
        return Path(output_path) if output_path else None


def _parse_manual(story_text: str):
    """Parse pipe-separated manual story or detect markdown format."""
    from vidgen.scriptgen import parse_markdown_story, parse_user_story, StorySettings
    text = story_text.strip()
    if text.startswith("#"):
        title, scenes, settings = parse_markdown_story(text)
        return scenes, settings
    scenes = parse_user_story(text)
    return scenes, StorySettings()


# Singleton
job_manager = JobManager()
