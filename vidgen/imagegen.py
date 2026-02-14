"""HuggingFace image generation with retry and fallback."""
from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import Callable

from PIL import Image

from .config import (
    API_IMAGE_HEIGHT,
    API_IMAGE_WIDTH,
    FALLBACK_IMAGE_MODEL,
    HEIGHT,
    MAX_RETRIES,
    PRIMARY_IMAGE_MODEL,
    RETRY_DELAY,
    WIDTH,
    Config,
)

log = logging.getLogger(__name__)


def _call_hf_image(
    prompt: str,
    model: str,
    token: str,
    width: int = API_IMAGE_WIDTH,
    height: int = API_IMAGE_HEIGHT,
) -> bytes:
    """Call HF Inference API for text-to-image. Returns raw image bytes."""
    from huggingface_hub import InferenceClient

    client = InferenceClient(model=model, token=token)
    img: Image.Image = client.text_to_image(
        prompt,
        width=width,
        height=height,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_image(
    prompt: str,
    output_path: Path,
    config: Config,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Generate an image from a text prompt and save to output_path.

    Tries PRIMARY_IMAGE_MODEL first, falls back to FALLBACK_IMAGE_MODEL.
    Retries up to MAX_RETRIES times per model.
    """
    models = [PRIMARY_IMAGE_MODEL, FALLBACK_IMAGE_MODEL]

    for model in models:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if progress_cb:
                    progress_cb(f"  Image gen: {model} (attempt {attempt}/{MAX_RETRIES})")
                log.info("Generating image with %s (attempt %d)", model, attempt)

                img_bytes = _call_hf_image(
                    prompt=prompt,
                    model=model,
                    token=config.hf_token,
                )

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(img_bytes)
                log.info("Saved image to %s", output_path)
                return output_path

            except Exception as e:
                log.warning("Image gen failed (%s attempt %d): %s", model, attempt, e)
                if progress_cb:
                    progress_cb(f"  ⚠ Failed ({model} attempt {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

        if progress_cb:
            progress_cb(f"  ⚠ All retries exhausted for {model}, trying fallback...")

    raise RuntimeError(f"Image generation failed for all models. Prompt: {prompt[:80]}...")


def generate_placeholder_image(
    prompt: str,
    output_path: Path,
    width: int = WIDTH,
    height: int = HEIGHT,
) -> Path:
    """Generate a simple placeholder image (no API needed). Used for testing."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (width, height), color=(30, 30, 50))
    draw = ImageDraw.Draw(img)

    # Draw prompt text wrapped
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except OSError:
        font = ImageFont.load_default()

    # Simple word wrap
    words = prompt.split()
    lines: list[str] = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > width - 80:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)

    y = height // 2 - len(lines) * 20
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (width - bbox[2]) // 2
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=(200, 200, 255), font=font)
        y += 40

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
