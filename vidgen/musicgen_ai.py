"""AI music generation using Facebook's MusicGen model.

Generates background music from text prompts like "warm acoustic strings,
soft piano motifs" using the MusicGen transformer model via the
HuggingFace transformers library.  Runs locally on CPU or GPU.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

# Default model — small (300M params) works on CPU in ~30-60s
DEFAULT_MUSIC_MODEL = "facebook/musicgen-small"

# MusicGen outputs at 32 kHz; ffmpeg resamples during audio mixing
MUSICGEN_SAMPLE_RATE = 32000

# ~1503 tokens ≈ 30 s of audio at 32 kHz / 50 tokens-per-second
DEFAULT_MAX_TOKENS = 1503


def generate_music_ai(
    output_path: Path,
    prompt: str = "peaceful background music, soft piano and strings",
    model_id: str = DEFAULT_MUSIC_MODEL,
    duration: float = 30.0,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Generate background music using MusicGen.

    Args:
        output_path: Where to save the WAV file.
        prompt: Text description of the desired music style.
        model_id: HuggingFace model ID for MusicGen.
        duration: Approximate target duration in seconds.
        progress_cb: Optional progress callback.

    Returns:
        Path to the generated WAV file.

    Raises:
        RuntimeError: If generation fails.
    """
    import numpy as np
    import scipy.io.wavfile as wavfile

    if progress_cb:
        progress_cb(f"  Loading MusicGen model ({model_id})...")

    try:
        import torch
        from transformers import AutoProcessor, MusicgenForConditionalGeneration

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if progress_cb:
            progress_cb(f"  Using device: {device}")

        processor = AutoProcessor.from_pretrained(model_id)
        model = MusicgenForConditionalGeneration.from_pretrained(model_id).to(device)

        # Calculate tokens for target duration (~50 tokens/sec for MusicGen)
        max_tokens = min(int(duration * 50), DEFAULT_MAX_TOKENS)

        if progress_cb:
            progress_cb(f"  Generating ~{duration:.0f}s of music: \"{prompt[:60]}\"...")

        inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)

        with torch.no_grad():
            audio_values = model.generate(**inputs, max_new_tokens=max_tokens)

        # audio_values shape: (batch, channels, samples)
        audio = audio_values[0, 0].cpu().numpy()

        # Normalize to int16 range
        audio = audio / (np.abs(audio).max() + 1e-8)
        audio_int16 = (audio * 32767).astype(np.int16)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wavfile.write(str(output_path), MUSICGEN_SAMPLE_RATE, audio_int16)

        actual_dur = len(audio) / MUSICGEN_SAMPLE_RATE
        if progress_cb:
            progress_cb(f"  AI music generated ({actual_dur:.1f}s)")

        log.info("MusicGen: saved %s (%.1fs)", output_path, actual_dur)
        return output_path

    except Exception as e:
        log.error("MusicGen generation failed: %s", e)
        raise RuntimeError(f"MusicGen failed: {e}") from e
