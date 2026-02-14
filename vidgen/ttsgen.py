"""Narrator voice generation using gTTS (Google Text-to-Speech).

Generates per-scene narration audio, times each clip to its scene duration,
then assembles a single narrator track that matches the full video timeline.
"""
from __future__ import annotations

import io
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

# Silence before narration starts within a scene (seconds)
NARRATION_LEAD_IN = 0.6


def _gtts_to_mp3(text: str) -> bytes:
    """Convert text to MP3 bytes via gTTS."""
    from gtts import gTTS

    tts = gTTS(text=text, lang="en", slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()


def _mp3_duration(mp3_path: Path) -> float:
    """Get duration of an MP3 using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=15)
    if result.returncode == 0:
        return float(result.stdout.strip())
    return 0.0


def _make_scene_audio(
    narration_mp3: Path,
    scene_duration: float,
    output_wav: Path,
    lead_in: float = NARRATION_LEAD_IN,
) -> Path:
    """Produce a WAV clip exactly scene_duration seconds long.

    Structure: lead_in silence | narration | silence padding to fill scene.
    If narration is longer than the scene, trim it.
    """
    speech_dur = _mp3_duration(narration_mp3)
    available = max(0.0, scene_duration - lead_in)
    trim_dur = min(speech_dur, available)

    # Build filter: silence pad before + narration (trimmed) + silence after
    silence_after = max(0.0, scene_duration - lead_in - trim_dur)

    # Use ffmpeg adelay + atrim + apad to build the final clip
    # Pipeline: decode mp3 → trim to available → delay by lead_in → pad to scene_duration
    filter_complex = (
        f"[0:a]atrim=0:{trim_dur},asetpts=PTS-STARTPTS[speech];"
        f"aevalsrc=0:d={lead_in}[silence_before];"
        f"aevalsrc=0:d={silence_after}[silence_after];"
        f"[silence_before][speech][silence_after]concat=n=3:v=0:a=1[out]"
    )

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(narration_mp3),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ar", "44100", "-ac", "1",
        "-t", str(scene_duration),
        str(output_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        log.warning("scene audio build failed: %s", result.stderr.decode(errors="replace")[-300:])
        # Fallback: silence of scene_duration
        _make_silence(output_wav, scene_duration)
    return output_wav


def _make_silence(output_wav: Path, duration: float) -> Path:
    """Generate a silent WAV of given duration."""
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration),
        str(output_wav),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=15)
    return output_wav


def generate_narration_track(
    scene_narrations: list[str],
    scene_durations: list[float],
    output_path: Path,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Generate a complete narrator audio track for the whole video.

    Each scene's narration is spoken at the right time offset, padded with
    silence to fill the scene duration, then all scenes are concatenated.

    Args:
        scene_narrations: Narration text per scene (in order).
        scene_durations: Duration in seconds per scene (same order).
        output_path: Where to save the final narrator WAV.
        progress_cb: Progress callback.

    Returns:
        Path to the narrator WAV file.
    """
    assert len(scene_narrations) == len(scene_durations), "mismatch"

    tmpdir = Path(tempfile.mkdtemp(prefix="vidgen_tts_"))
    scene_wavs: list[Path] = []

    for i, (text, dur) in enumerate(zip(scene_narrations, scene_durations)):
        if progress_cb:
            progress_cb(f"  Narrating scene {i}: \"{text[:50]}{'...' if len(text) > 50 else ''}\"")

        try:
            # Generate TTS audio
            mp3_bytes = _gtts_to_mp3(text)
            mp3_path = tmpdir / f"speech_{i:03d}.mp3"
            mp3_path.write_bytes(mp3_bytes)

            # Build timed scene audio (lead-in + speech + padding)
            wav_path = tmpdir / f"scene_{i:03d}.wav"
            _make_scene_audio(mp3_path, dur, wav_path)
            scene_wavs.append(wav_path)

        except Exception as e:
            log.warning("TTS failed for scene %d: %s — using silence", i, e)
            if progress_cb:
                progress_cb(f"  ⚠ TTS scene {i} failed: {e}")
            silence_wav = tmpdir / f"scene_{i:03d}.wav"
            _make_silence(silence_wav, dur)
            scene_wavs.append(silence_wav)

    if not scene_wavs:
        raise RuntimeError("No narration clips generated.")

    if progress_cb:
        progress_cb("  Assembling full narration timeline...")

    # Concatenate all scene wavs into one continuous track
    list_file = tmpdir / "narration_list.txt"
    with open(list_file, "w") as f:
        for wav in scene_wavs:
            f.write(f"file '{wav}'\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-ar", "44100", "-ac", "1",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(
            f"Narration concat failed: {result.stderr.decode(errors='replace')[-300:]}"
        )

    if progress_cb:
        size_kb = output_path.stat().st_size // 1024
        total_dur = sum(scene_durations)
        progress_cb(f"  ✓ Narration track: {total_dur:.0f}s · {size_kb} KB")

    return output_path
