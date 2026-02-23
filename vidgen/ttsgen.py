"""Narrator voice generation using Microsoft Edge TTS (neural voices).

Generates per-scene narration audio using natural, high-quality neural voices,
times each clip to its scene duration, then assembles a single narrator track
that matches the full video timeline.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from .config import NARRATION_LEAD_IN, NARRATION_PADDING_AFTER
from .scriptgen import Scene

log = logging.getLogger(__name__)

# Edge TTS voice — deep, authoritative, sensational documentary style.
# Alternatives: "en-US-DavisNeural" (dramatic), "en-US-AriaNeural" (expressive female)
EDGE_TTS_VOICE = "en-US-GuyNeural"
EDGE_TTS_RATE  = "-8%"    # slightly slower for gravitas
EDGE_TTS_PITCH = "-5Hz"   # slightly lower pitch for depth


async def _edge_tts_to_mp3_async(text: str, output_path: Path) -> None:
    """Generate MP3 from text using Microsoft Edge TTS (async)."""
    import edge_tts
    communicate = edge_tts.Communicate(
        text,
        voice=EDGE_TTS_VOICE,
        rate=EDGE_TTS_RATE,
        pitch=EDGE_TTS_PITCH,
    )
    await communicate.save(str(output_path))


def _edge_tts_to_mp3(text: str, output_path: Path) -> None:
    """Generate MP3 from text using Microsoft Edge TTS (sync wrapper)."""
    asyncio.run(_edge_tts_to_mp3_async(text, output_path))


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
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return 0.0


def sync_scene_durations_to_narration(
    scenes: list[Scene],
    progress_cb: Callable[[str], None] | None = None,
) -> list[Scene]:
    """Measure actual TTS narration duration and adjust scene durations to fit.

    For each scene:
      1. Generate TTS audio (MP3)
      2. Measure actual speech duration
      3. Adjust scene.duration = max(original, lead_in + speech + padding_after)

    This ensures narration is never cut off mid-sentence.
    """
    if progress_cb:
        progress_cb("🎙️  Syncing scene durations to narration timing...")

    tmpdir = Path(tempfile.mkdtemp(prefix="vidgen_tts_sync_"))

    for scene in scenes:
        try:
            mp3_path = tmpdir / f"sync_{scene.index:03d}.mp3"
            _edge_tts_to_mp3(scene.narration, mp3_path)

            speech_dur = _mp3_duration(mp3_path)
            required_dur = NARRATION_LEAD_IN + speech_dur + NARRATION_PADDING_AFTER

            if scene.duration < required_dur:
                if progress_cb:
                    progress_cb(
                        f"  Scene {scene.index}: {scene.duration:.1f}s → "
                        f"{required_dur:.1f}s (speech {speech_dur:.1f}s)"
                    )
                scene.duration = round(required_dur, 1)
            else:
                if progress_cb:
                    progress_cb(
                        f"  Scene {scene.index}: {scene.duration:.1f}s OK "
                        f"(speech {speech_dur:.1f}s fits)"
                    )

        except Exception as e:
            log.warning("TTS sync failed for scene %d: %s — keeping original duration", scene.index, e)
            if progress_cb:
                progress_cb(f"  Scene {scene.index}: sync failed ({e}), keeping {scene.duration}s")

    shutil.rmtree(tmpdir, ignore_errors=True)

    total_dur = sum(s.duration for s in scenes)
    if progress_cb:
        progress_cb(f"  ✓ Total duration after sync: {total_dur:.0f}s")

    return scenes


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
    silence_after = max(0.0, scene_duration - lead_in - trim_dur)

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
        _make_silence(output_wav, scene_duration)
    return output_wav


def _make_silence(output_wav: Path, duration: float) -> Path:
    """Generate a silent WAV of given duration."""
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
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
    """
    assert len(scene_narrations) == len(scene_durations), "mismatch"

    tmpdir = Path(tempfile.mkdtemp(prefix="vidgen_tts_"))
    scene_wavs: list[Path] = []

    for i, (text, dur) in enumerate(zip(scene_narrations, scene_durations)):
        if progress_cb:
            progress_cb(f"  Narrating scene {i}: \"{text[:50]}{'...' if len(text) > 50 else ''}\"")

        try:
            mp3_path = tmpdir / f"speech_{i:03d}.mp3"
            _edge_tts_to_mp3(text, mp3_path)

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
        progress_cb(f"  ✓ Narration track ({EDGE_TTS_VOICE}): {total_dur:.0f}s · {size_kb} KB")

    return output_path
