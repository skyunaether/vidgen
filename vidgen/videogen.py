"""HuggingFace video generation (image-to-video) with retry."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from .config import MAX_RETRIES, RETRY_DELAY, VIDEO_MODEL, Config

log = logging.getLogger(__name__)


def _call_hf_img2vid(
    image_path: Path,
    model: str,
    token: str,
) -> bytes:
    """Call HF Inference API for image-to-video. Returns raw video bytes."""
    from huggingface_hub import InferenceClient

    client = InferenceClient(model=model, token=token)
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    result = client.image_to_video(image_bytes)
    # Result may be bytes or a path-like
    if isinstance(result, (bytes, bytearray)):
        return bytes(result)
    # If it returned a path
    return Path(result).read_bytes()


def generate_video(
    image_path: Path,
    output_path: Path,
    config: Config,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Animate a still image into a short video clip.

    Uses stable-video-diffusion-img2vid-xt via HF API.
    Retries up to MAX_RETRIES on failure.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if progress_cb:
                progress_cb(f"  Video gen: {VIDEO_MODEL} (attempt {attempt}/{MAX_RETRIES})")
            log.info("Generating video from %s (attempt %d)", image_path, attempt)

            vid_bytes = _call_hf_img2vid(
                image_path=image_path,
                model=VIDEO_MODEL,
                token=config.hf_token,
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(vid_bytes)
            log.info("Saved video clip to %s", output_path)
            return output_path

        except StopIteration:
            # Model not available on the serverless inference API — no point retrying
            msg = f"Model {VIDEO_MODEL} not available on HF serverless API"
            log.warning(msg)
            if progress_cb:
                progress_cb(f"  ⚠ {msg} — will use Ken Burns effect instead")
            raise RuntimeError(msg)
        except Exception as e:
            log.warning("Video gen failed (attempt %d): %s", attempt, e)
            if progress_cb:
                progress_cb(f"  ⚠ Video gen failed (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(f"Video generation failed after {MAX_RETRIES} attempts for {image_path}")


def generate_placeholder_video(
    image_path: Path,
    output_path: Path,
    duration: float = 4.0,
) -> Path:
    """Create a placeholder video from a still image using ffmpeg (no API).

    Applies a gentle zoom for visual interest.
    """
    import subprocess

    output_path.parent.mkdir(parents=True, exist_ok=True)

    frames = int(duration * 30)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-t", str(duration),
        "-vf", (
            f"scale=1200x2134,zoompan=z='min(zoom+0.002,1.08)'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1080x1920:fps=30"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        # Fallback: simple static frame video
        cmd2 = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-t", str(duration),
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", "30",
            str(output_path),
        ]
        subprocess.run(cmd2, capture_output=True, check=True, timeout=120)
    return output_path
