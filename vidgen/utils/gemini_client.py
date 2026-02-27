"""Gemini video generation client."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from google import genai
import requests

from ..config import Config

log = logging.getLogger(__name__)


def _download_video(url: str, output_path: Path, api_key: str) -> Path:
    """Download video from URI to local path (requires API key auth)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {"x-goog-api-key": api_key}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return output_path


def generate_video_gemini(
    prompt: str,
    output_path: Path,
    config: Config,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Generate a video using Google Veo via the Gemini API."""
    if not config.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=config.gemini_api_key)
    model_id = "veo-2.0-generate-001"

    if progress_cb:
        progress_cb(f"  Video gen: Google Veo ({model_id}) - Submitting job...")

    log.info("Generating video with Gemini Veo: %s", prompt)

    operation = client.models.generate_videos(
        model=model_id,
        prompt=prompt,
    )

    if progress_cb:
        progress_cb("  Video gen: Job submitted, waiting for completion (can take a few minutes)...")

    # Poll until done — operation.done is None initially, True when finished
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    if operation.error:
        msg = f"Veo generation failed: {operation.error}"
        log.error(msg)
        raise RuntimeError(msg)

    # response and result both hold GenerateVideoResponse; use response
    video_response = operation.response or operation.result
    if not video_response:
        raise RuntimeError("Veo operation completed but returned no response.")

    generated = getattr(video_response, "generated_videos", None)
    if not generated:
        raise RuntimeError(f"No generated videos in response: {video_response}")

    video_uri = generated[0].video.uri
    if not video_uri:
        raise RuntimeError(f"Video URI is empty in response: {video_response}")

    log.info("Veo video URI: %s", video_uri)

    if progress_cb:
        progress_cb(f"  Video gen: Download ready! Saving to {output_path.name}...")

    return _download_video(video_uri, output_path, config.gemini_api_key)
