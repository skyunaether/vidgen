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

# AI music generation (MusicGen)
DEFAULT_MUSIC_MODEL = "facebook/musicgen-small"

# AI TTS (Parler-TTS)
DEFAULT_TTS_MODEL = "parler-tts/parler-tts-mini-v1"

# Ken Burns
KB_ZOOM_MIN = 1.0
KB_ZOOM_MAX = 1.15  # 15% zoom – more cinematic motion
KB_OVERSCAN = 1.35  # 35% overscan so pans don't reveal black edges

# Transitions – cycled per scene for visual variety
CROSSFADE_DURATION = 0.8  # seconds
TRANSITION_TYPES = [
    "fade",        # classic dissolve
    "slideleft",   # slide incoming from right
    "smoothleft",  # smooth directional wipe
    "circlecrop",  # circular iris reveal
    "slideup",     # slide incoming from bottom
    "diagtl",      # diagonal wipe top-left
]

# Text overlay
TEXT_FONT_SIZE = 42
TEXT_SHADOW_OFFSET = 3

# Narration timing sync
NARRATION_LEAD_IN = 0.6         # silence before speech starts (seconds)
NARRATION_PADDING_AFTER = 1.0   # silence after speech ends (seconds)
# Total scene duration = lead_in + speech_duration + padding_after

# Retry
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


@dataclass
class Config:
    hf_token: str = ""
    gemini_api_key: str = ""
    output_dir: Path = field(default_factory=lambda: Path("output"))
    bg_music: str | None = None  # path to background music file
    use_ai_music: bool = True    # use MusicGen (falls back to procedural)
    use_ai_tts: bool = False     # use Parler-TTS (default: Edge TTS)
    music_model: str = DEFAULT_MUSIC_MODEL
    tts_model: str = DEFAULT_TTS_MODEL

    @classmethod
    def load(cls) -> "Config":
        """Load config from env vars then config file."""
        cfg = cls()

        # Env var takes priority
        token = os.environ.get("HF_TOKEN", "")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")

        # Fall back to config file
        if (not token or not gemini_key) and CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
                if not token:
                    token = data.get("hf_token", "")
                if not gemini_key:
                    gemini_key = data.get("gemini_api_key", "")
                if music := data.get("bg_music"):
                    cfg.bg_music = music
                if out := data.get("output_dir"):
                    cfg.output_dir = Path(out)
                if data.get("use_ai_music") is not None:
                    cfg.use_ai_music = bool(data["use_ai_music"])
                if data.get("use_ai_tts") is not None:
                    cfg.use_ai_tts = bool(data["use_ai_tts"])
                if mm := data.get("music_model"):
                    cfg.music_model = mm
                if tm := data.get("tts_model"):
                    cfg.tts_model = tm
            except (json.JSONDecodeError, OSError):
                pass

        cfg.hf_token = token
        cfg.gemini_api_key = gemini_key
        return cfg

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"hf_token": self.hf_token, "gemini_api_key": self.gemini_api_key}
        if self.bg_music:
            data["bg_music"] = self.bg_music
        data["use_ai_music"] = self.use_ai_music
        data["use_ai_tts"] = self.use_ai_tts
        data["music_model"] = self.music_model
        data["tts_model"] = self.tts_model
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
