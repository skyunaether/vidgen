"""Config read/write routes."""
from __future__ import annotations

import sys
from pathlib import Path

from litestar import get, post
from litestar.exceptions import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from vidgen.config import Config
from webui.backend.models import ConfigPayload


@get("/api/config")
async def get_config() -> ConfigPayload:
    cfg = Config.load()
    return ConfigPayload(
        # Mask secret keys — show only last 6 chars
        hf_token=_mask(cfg.hf_token),
        gemini_api_key=_mask(cfg.gemini_api_key),
        output_dir=str(cfg.output_dir),
        use_ai_music=cfg.use_ai_music,
        use_ai_tts=cfg.use_ai_tts,
        music_model=cfg.music_model,
        tts_model=cfg.tts_model,
    )


@post("/api/config")
async def save_config(data: ConfigPayload) -> dict:
    cfg = Config.load()
    # Only update secrets if the user sent a non-masked value
    if data.hf_token and not data.hf_token.endswith("…"):
        cfg.hf_token = data.hf_token
    if data.gemini_api_key and not data.gemini_api_key.endswith("…"):
        cfg.gemini_api_key = data.gemini_api_key
    cfg.output_dir = Path(data.output_dir)
    cfg.use_ai_music = data.use_ai_music
    cfg.use_ai_tts = data.use_ai_tts
    cfg.music_model = data.music_model
    cfg.tts_model = data.tts_model
    cfg.save()
    return {"ok": True}


def _mask(value: str) -> str:
    if not value:
        return ""
    return value[:4] + "…" + value[-4:] if len(value) > 8 else "…"
