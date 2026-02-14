"""Settings and API key management."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".vidgen"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Video output specs
WIDTH = 1080
HEIGHT = 1920
FPS = 30
CROSSFADE_DURATION = 0.5  # seconds

# Image generation
# FLUX.1-schnell: free tier, fast, no gating (FLUX.1-dev requires HF Pro)
PRIMARY_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
FALLBACK_IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

# API image dimensions — portrait 9:16, within free-tier inference limits.
# ffmpeg scales up to full 1080x1920 output resolution.
API_IMAGE_WIDTH = 576
API_IMAGE_HEIGHT = 1024

# Video generation (image-to-video)
VIDEO_MODEL = "stabilityai/stable-video-diffusion-img2vid-xt"

# Ken Burns
KB_ZOOM_MIN = 1.0
KB_ZOOM_MAX = 1.08  # 8% zoom

# Text overlay
TEXT_FONT_SIZE = 42
TEXT_SHADOW_OFFSET = 3

# Retry
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


@dataclass
class Config:
    hf_token: str = ""
    output_dir: Path = field(default_factory=lambda: Path("output"))
    bg_music: str | None = None  # path to background music file

    @classmethod
    def load(cls) -> "Config":
        """Load config from env vars then config file."""
        cfg = cls()

        # Env var takes priority
        token = os.environ.get("HF_TOKEN", "")

        # Fall back to config file
        if not token and CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                token = data.get("hf_token", "")
                if music := data.get("bg_music"):
                    cfg.bg_music = music
                if out := data.get("output_dir"):
                    cfg.output_dir = Path(out)
            except (json.JSONDecodeError, OSError):
                pass

        cfg.hf_token = token
        return cfg

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"hf_token": self.hf_token}
        if self.bg_music:
            data["bg_music"] = self.bg_music
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
