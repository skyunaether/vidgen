"""Pydantic request/response models for the VidGen Web API."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class PipelineOptions(BaseModel):
    story_review: bool = True   # Stage 1.5: AI reviewer-refiner loop
    image_gen: bool = True      # Stage 2: image generation
    video_gen: bool = True      # Stage 3: video animation
    narration: bool = True      # Stage 4: TTS narration
    music_gen: bool = True      # Stage 4.5: background music
    compile: bool = True        # Stage 5: final compilation


class MultiAgentOptions(BaseModel):
    enabled: bool = False
    max_iterations: int = Field(default=3, ge=1, le=10)


class ExecuteRequest(BaseModel):
    mode: Literal["auto", "manual", "files"] = "auto"
    prompt: str = ""            # auto mode: free-form topic
    story: str = ""             # manual mode: pipe-separated scene lines
    files_path: str = ""        # files mode: path or glob to .md files
    use_test_mode: bool = False # placeholder images — no API calls
    pipeline: PipelineOptions = Field(default_factory=PipelineOptions)
    multi_agent: MultiAgentOptions = Field(default_factory=MultiAgentOptions)
    # Per-request config overrides (applied on top of ~/.vidgen/config.json)
    use_ai_music: bool | None = None
    use_ai_tts: bool | None = None


class JobStatus(BaseModel):
    job_id: str
    state: Literal["queued", "running", "done", "cancelled", "failed"]
    started_at: float | None = None
    finished_at: float | None = None
    output_path: str | None = None
    error: str | None = None


class ConfigPayload(BaseModel):
    hf_token: str = ""
    gemini_api_key: str = ""
    output_dir: str = "output"
    use_ai_music: bool = True
    use_ai_tts: bool = False
    music_model: str = "facebook/musicgen-small"
    tts_model: str = "parler-tts/parler-tts-mini-v1"


class OutputFile(BaseModel):
    name: str
    path: str
    size_bytes: int
    created_at: float
