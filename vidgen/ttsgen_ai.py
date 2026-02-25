"""AI text-to-speech using Parler-TTS.

Generates high-quality narration from text with voice style controlled by
a natural language description (e.g. "calm male narrator, warm tone").
Requires: pip install git+https://github.com/huggingface/parler-tts.git
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

DEFAULT_TTS_MODEL = "parler-tts/parler-tts-mini-v1"
PARLER_SAMPLE_RATE = 44100

# Default voice description when none is provided
DEFAULT_VOICE_DESC = (
    "A male narrator with a calm, warm tone, speaking at a moderate pace "
    "in a documentary style with clear diction and gentle authority."
)


def generate_speech_ai(
    text: str,
    output_path: Path,
    voice_description: str = DEFAULT_VOICE_DESC,
    model_id: str = DEFAULT_TTS_MODEL,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Generate speech audio using Parler-TTS.

    Args:
        text: The text to speak.
        output_path: Where to save the WAV file.
        voice_description: Natural language description of the voice style.
        model_id: HuggingFace model ID for Parler-TTS.
        progress_cb: Optional progress callback.

    Returns:
        Path to the generated WAV file.

    Raises:
        RuntimeError: If generation fails.
    """
    import numpy as np
    import scipy.io.wavfile as wavfile

    if progress_cb:
        progress_cb(f"  Loading Parler-TTS model ({model_id})...")

    try:
        import torch
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"

        model = ParlerTTSForConditionalGeneration.from_pretrained(model_id).to(device)
        tokenizer = AutoTokenizer.from_pretrained(model_id)

        if progress_cb:
            progress_cb(f"  Generating speech ({device}): \"{text[:50]}...\"")

        # Tokenize the voice description and text separately
        input_ids = tokenizer(voice_description, return_tensors="pt").input_ids.to(device)
        prompt_input_ids = tokenizer(text, return_tensors="pt").input_ids.to(device)

        with torch.no_grad():
            generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_input_ids)

        audio = generation.cpu().numpy().squeeze()

        # Normalize
        audio = audio / (np.abs(audio).max() + 1e-8)
        audio_int16 = (audio * 32767).astype(np.int16)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wavfile.write(str(output_path), PARLER_SAMPLE_RATE, audio_int16)

        actual_dur = len(audio) / PARLER_SAMPLE_RATE
        if progress_cb:
            progress_cb(f"  AI speech generated ({actual_dur:.1f}s)")

        log.info("Parler-TTS: saved %s (%.1fs)", output_path, actual_dur)
        return output_path

    except ImportError:
        raise RuntimeError(
            "Parler-TTS not installed. Run: "
            "pip install git+https://github.com/huggingface/parler-tts.git"
        )
    except Exception as e:
        log.error("Parler-TTS failed: %s", e)
        raise RuntimeError(f"Parler-TTS failed: {e}") from e
