"""Procedural background music generator.

Generates an epic orchestral score tailored to the story mood using
multi-layer synthesis: strings, brass, bass, and a pad/choir layer.
No external API or model required — pure numpy synthesis.
"""
from __future__ import annotations

import logging
import struct
import wave
from pathlib import Path
from typing import Callable

import numpy as np

log = logging.getLogger(__name__)

SR = 44100  # sample rate


# ---------------------------------------------------------------------------
# Low-level synthesis helpers
# ---------------------------------------------------------------------------

def _note(freq: float, duration: float, sr: int = SR) -> np.ndarray:
    """Return a sine-wave tone at freq Hz for duration seconds."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _adsr(signal: np.ndarray, attack: float, decay: float, sustain: float,
          release: float, sr: int = SR) -> np.ndarray:
    """Apply an ADSR envelope to a signal (all times in seconds)."""
    n = len(signal)
    env = np.ones(n, dtype=np.float32)
    a = int(attack * sr)
    d = int(decay * sr)
    r = int(release * sr)
    s_level = sustain

    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if d > 0 and a + d < n:
        env[a:a + d] = np.linspace(1, s_level, d)
    if a + d < n:
        env[a + d:max(n - r, a + d)] = s_level
    if r > 0 and n - r > 0:
        env[max(n - r, 0):] = np.linspace(s_level, 0, min(r, n))

    return signal * env


def _harmonics(freq: float, duration: float, weights: list[float],
               sr: int = SR) -> np.ndarray:
    """Sum harmonics of freq with given amplitude weights."""
    out = np.zeros(int(sr * duration), dtype=np.float32)
    for i, w in enumerate(weights, start=1):
        out += w * _note(freq * i, duration, sr)
    return out


def _detune_chorus(freq: float, duration: float, n_voices: int = 3,
                   detune_cents: float = 8.0, sr: int = SR) -> np.ndarray:
    """Simulate a chorus/ensemble by layering slightly detuned voices."""
    out = np.zeros(int(sr * duration), dtype=np.float32)
    cents = np.linspace(-detune_cents, detune_cents, n_voices)
    for c in cents:
        f = freq * (2 ** (c / 1200))
        out += _note(f, duration, sr)
    return out / n_voices


def _fade(signal: np.ndarray, fade_in: float = 0.0, fade_out: float = 0.0,
          sr: int = SR) -> np.ndarray:
    """Fade in/out at start and end."""
    sig = signal.copy()
    fi = int(fade_in * sr)
    fo = int(fade_out * sr)
    if fi > 0 and fi <= len(sig):
        sig[:fi] *= np.linspace(0, 1, fi)
    if fo > 0 and fo <= len(sig):
        sig[-fo:] *= np.linspace(1, 0, fo)
    return sig


def _normalize(signal: np.ndarray, peak: float = 0.85) -> np.ndarray:
    m = np.max(np.abs(signal))
    if m > 0:
        return (signal / m * peak).astype(np.float32)
    return signal


# ---------------------------------------------------------------------------
# Chord / note frequency tables (equal temperament, A4=440)
# ---------------------------------------------------------------------------

def _midi_to_hz(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


# Note MIDI numbers (C4 = 60)
_NOTES = {
    "C2": 36, "D2": 38, "E2": 40, "F2": 41, "G2": 43, "A2": 45, "B2": 47,
    "C3": 48, "D3": 50, "E3": 52, "F3": 53, "G3": 55, "A3": 57, "B3": 59,
    "C4": 60, "D4": 62, "E4": 64, "F4": 65, "G4": 67, "A4": 69, "B4": 71,
    "C5": 72, "D5": 74, "E5": 76, "G5": 79,
}


def _hz(name: str) -> float:
    return _midi_to_hz(_NOTES[name])


# ---------------------------------------------------------------------------
# Music sections
# ---------------------------------------------------------------------------
# Chord progression: Em – C – G – D (classic cinematic/epic progression)
# 4 chords × N bars, each bar = 4 beats at ~72 BPM → beat = 0.833 s, bar = 3.33 s

BPM = 72
BEAT = 60.0 / BPM        # 0.833 s
BAR = BEAT * 4            # 3.33 s

# Chord root frequencies (bass register)
_CHORDS = [
    # (bass, chord tones mid, chord tones high)
    ("E2", ["E3", "G3", "B3"], ["E4", "B4"]),   # Em
    ("C2", ["C3", "E3", "G3"], ["C4", "G4"]),   # C
    ("G2", ["G3", "B3", "D4"], ["G4", "D5"]),   # G
    ("D2", ["D3", "F3", "A3"], ["D4", "A4"]),   # D  (Dadd9 feel)
]


def _bass_layer(duration: float, sr: int = SR) -> np.ndarray:
    """Deep, warm bass notes on chord roots."""
    out = np.zeros(int(sr * duration), dtype=np.float32)
    n_bars = int(duration / BAR)
    for bar in range(n_bars):
        chord_idx = bar % len(_CHORDS)
        root, _, _ = _CHORDS[chord_idx]
        f = _hz(root)
        t0 = int(bar * BAR * sr)
        seg = _harmonics(f, BAR, weights=[1.0, 0.4, 0.15, 0.05], sr=sr)
        seg = _adsr(seg, attack=0.05, decay=0.1, sustain=0.7, release=0.4, sr=sr)
        end = min(t0 + len(seg), len(out))
        out[t0:end] += seg[:end - t0]
    return out * 0.55


def _strings_layer(duration: float, sr: int = SR) -> np.ndarray:
    """Sustained string pad using detuned chorus + slow attack."""
    out = np.zeros(int(sr * duration), dtype=np.float32)
    n_bars = int(duration / BAR)
    for bar in range(n_bars):
        chord_idx = bar % len(_CHORDS)
        _, mid_notes, _ = _CHORDS[chord_idx]
        for note in mid_notes:
            f = _hz(note)
            seg = _detune_chorus(f, BAR, n_voices=4, detune_cents=10.0, sr=sr)
            seg = _adsr(seg, attack=0.6, decay=0.2, sustain=0.8, release=0.5, sr=sr)
            t0 = int(bar * BAR * sr)
            end = min(t0 + len(seg), len(out))
            out[t0:end] += seg[:end - t0]
    return out * 0.28


def _brass_layer(duration: float, sr: int = SR) -> np.ndarray:
    """Brass hits on bars 1, 3, 5... (odd bars) for power and drive."""
    out = np.zeros(int(sr * duration), dtype=np.float32)
    n_bars = int(duration / BAR)
    for bar in range(n_bars):
        if bar % 2 != 0:
            continue
        chord_idx = bar % len(_CHORDS)
        _, _, high_notes = _CHORDS[chord_idx]
        for note in high_notes:
            f = _hz(note)
            seg_dur = BAR * 0.75
            seg = _harmonics(f, seg_dur, weights=[1.0, 0.6, 0.3, 0.1], sr=sr)
            seg = _adsr(seg, attack=0.08, decay=0.15, sustain=0.65, release=0.3, sr=sr)
            t0 = int(bar * BAR * sr)
            end = min(t0 + len(seg), len(out))
            out[t0:end] += seg[:end - t0]
    return out * 0.32


def _choir_pad(duration: float, sr: int = SR) -> np.ndarray:
    """Warm choir-like pad using slow-attack detuned voices for warmth."""
    out = np.zeros(int(sr * duration), dtype=np.float32)
    n_bars = int(duration / BAR)
    for bar in range(0, n_bars, 2):  # every 2 bars
        chord_idx = bar % len(_CHORDS)
        _, mid_notes, high_notes = _CHORDS[chord_idx]
        for note in mid_notes[:2] + high_notes[:1]:
            f = _hz(note) * 0.5  # octave down for warmth
            seg = _detune_chorus(f, BAR * 2, n_voices=3, detune_cents=6.0, sr=sr)
            seg = _adsr(seg, attack=1.2, decay=0.3, sustain=0.6, release=0.8, sr=sr)
            t0 = int(bar * BAR * sr)
            seg_len = min(len(seg), len(out) - t0)
            out[t0:t0 + seg_len] += seg[:seg_len]
    return out * 0.18


def _dynamics_envelope(duration: float, sr: int = SR) -> np.ndarray:
    """Master dynamics: soft intro → build → peak → gentle ending."""
    n = int(sr * duration)
    env = np.ones(n, dtype=np.float32)
    # Soft start (first 10%)
    fade_in = int(n * 0.10)
    env[:fade_in] = np.linspace(0.2, 1.0, fade_in)
    # Fade out (last 8%)
    fade_out = int(n * 0.08)
    env[-fade_out:] = np.linspace(1.0, 0.0, fade_out)
    # Gradual swell in middle
    mid = n // 2
    swell_start = int(n * 0.30)
    swell_peak = int(n * 0.65)
    swell = np.ones(n, dtype=np.float32)
    swell[swell_start:swell_peak] = np.linspace(1.0, 1.25, swell_peak - swell_start)
    swell[swell_peak:n - fade_out] = np.linspace(1.25, 1.0, n - fade_out - swell_peak)
    return np.clip(env * swell, 0, 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_music(
    output_path: Path,
    duration: float = 32.0,
    mood: str = "epic",
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Generate a background music WAV file.

    Args:
        output_path: Where to save the .wav file.
        duration: Length in seconds (will be looped by ffmpeg if shorter than video).
        mood: Hint for future mood-selection logic (currently always epic/orchestral).
        progress_cb: Progress callback.

    Returns:
        Path to the generated WAV file.
    """
    if progress_cb:
        progress_cb(f"  Composing background music ({duration:.0f}s, {BPM} BPM)...")

    log.info("Generating %s background music, %.0f seconds", mood, duration)

    # Extend duration to a whole number of bars
    n_bars = max(4, int(np.ceil(duration / BAR)))
    dur = n_bars * BAR

    bass = _bass_layer(dur)
    strings = _strings_layer(dur)
    brass = _brass_layer(dur)
    choir = _choir_pad(dur)

    mix = bass + strings + brass + choir
    mix *= _dynamics_envelope(dur)
    mix = _normalize(mix, peak=0.80)

    # Trim to requested duration
    mix = mix[:int(SR * duration)]

    # Write WAV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SR)
        pcm = (mix * 32767).astype(np.int16).tobytes()
        wf.writeframes(pcm)

    if progress_cb:
        progress_cb(f"  ✓ Music generated: {output_path.name} ({output_path.stat().st_size // 1024} KB)")

    log.info("Music saved to %s", output_path)
    return output_path
