"""Procedural background music generator — Chinese traditional style.

Generates a peaceful, harmonious score inspired by traditional Chinese music,
using the D major pentatonic scale and simulated instruments: erhu (bowed
string), guzheng (plucked zither), dizi (bamboo flute), and a tonic drone.
No external API or model required — pure numpy synthesis.
"""
from __future__ import annotations

import logging
import wave
from pathlib import Path
from typing import Callable

import numpy as np

log = logging.getLogger(__name__)

SR = 44100  # sample rate

# ---------------------------------------------------------------------------
# Tempo — slow and meditative for peace and harmony
# ---------------------------------------------------------------------------

BPM  = 60
BEAT = 60.0 / BPM   # 1.0 s per beat
BAR  = BEAT * 4     # 4.0 s per bar


# ---------------------------------------------------------------------------
# D major pentatonic scale (D E F# A B) — the backbone of Chinese melody
# ---------------------------------------------------------------------------

def _midi_to_hz(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


_PENTA: dict[str, float] = {
    "D2":  _midi_to_hz(38),
    "A2":  _midi_to_hz(45),
    "D3":  _midi_to_hz(50),
    "E3":  _midi_to_hz(52),
    "Fs3": _midi_to_hz(54),
    "A3":  _midi_to_hz(57),
    "B3":  _midi_to_hz(59),
    "D4":  _midi_to_hz(62),
    "E4":  _midi_to_hz(64),
    "Fs4": _midi_to_hz(66),
    "A4":  _midi_to_hz(69),
    "B4":  _midi_to_hz(71),
    "D5":  _midi_to_hz(74),
}

def _p(name: str) -> float:
    return _PENTA[name]


# ---------------------------------------------------------------------------
# Low-level synthesis helpers
# ---------------------------------------------------------------------------

def _adsr(signal: np.ndarray, attack: float, decay: float, sustain: float,
          release: float, sr: int = SR) -> np.ndarray:
    """Apply ADSR envelope (all times in seconds)."""
    n = len(signal)
    env = np.ones(n, dtype=np.float32)
    a = int(attack * sr)
    d = int(decay * sr)
    r = int(release * sr)

    a_end = min(a, n)
    if a > 0:
        env[:a_end] = np.linspace(0.0, 1.0, a_end)

    d_start = a_end
    d_end = min(a + d, n)
    if d_end > d_start:
        env[d_start:d_end] = np.linspace(1.0, sustain, d_end - d_start)

    s_start = min(a + d, n)
    r_start = max(n - r, s_start)
    if r_start > s_start:
        env[s_start:r_start] = sustain

    if r_start < n:
        env[r_start:] = np.linspace(sustain, 0.0, n - r_start)

    return signal * env


def _harmonics(freq: float, duration: float, weights: list[float],
               sr: int = SR) -> np.ndarray:
    """Sum harmonic partials with given amplitude weights."""
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    out = np.zeros(n, dtype=np.float32)
    for i, w in enumerate(weights, start=1):
        out += w * np.sin(2 * np.pi * freq * i * t).astype(np.float32)
    return out


def _vibrato_tone(freq: float, duration: float, rate: float = 5.5,
                  cents: float = 14.0, onset: float = 0.20,
                  sr: int = SR) -> np.ndarray:
    """Sine wave with gradually-applied vibrato — gives erhu/bowed character."""
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    vib_hz = freq * (2 ** (cents / 1200) - 1)

    # Vibrato envelope: ramp up after onset
    onset_s = int(onset * sr)
    vib_env = np.zeros(n, dtype=np.float32)
    if onset_s < n:
        ramp = min(int(0.25 * sr), n - onset_s)
        vib_env[onset_s:onset_s + ramp] = np.linspace(0.0, 1.0, ramp)
        if onset_s + ramp < n:
            vib_env[onset_s + ramp:] = 1.0

    # Frequency-modulate then integrate to phase
    freq_t = freq + vib_hz * np.sin(2 * np.pi * rate * t) * vib_env
    phase = 2 * np.pi * np.cumsum(freq_t) / sr
    return np.sin(phase).astype(np.float32)


def _normalize(signal: np.ndarray, peak: float = 0.78) -> np.ndarray:
    m = np.max(np.abs(signal))
    if m > 0:
        return (signal / m * peak).astype(np.float32)
    return signal


# ---------------------------------------------------------------------------
# Instrument voices
# ---------------------------------------------------------------------------

def _erhu(freq: float, dur: float, sr: int = SR) -> np.ndarray:
    """二胡 Erhu — warm bowed string with expressive vibrato."""
    sig = _vibrato_tone(freq, dur, rate=5.5, cents=14.0, onset=0.20, sr=sr)
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    # Add upper harmonics (no vibrato on harmonics, like a real bowed string)
    sig = sig + 0.38 * np.sin(2 * np.pi * freq * 2 * t).astype(np.float32)
    sig = sig + 0.14 * np.sin(2 * np.pi * freq * 3 * t).astype(np.float32)
    sig = sig + 0.05 * np.sin(2 * np.pi * freq * 4 * t).astype(np.float32)
    return _adsr(sig.astype(np.float32),
                 attack=0.12, decay=0.15, sustain=0.85, release=0.45, sr=sr)


def _guzheng(freq: float, dur: float, sr: int = SR) -> np.ndarray:
    """古筝 Guzheng — bright plucked zither, fast attack, natural decay."""
    sig = _harmonics(freq, dur, weights=[1.0, 0.55, 0.28, 0.09, 0.03], sr=sr)
    return _adsr(sig, attack=0.004, decay=0.28, sustain=0.18, release=0.50, sr=sr)


def _dizi(freq: float, dur: float, sr: int = SR) -> np.ndarray:
    """笛子 Dizi — clear bamboo flute, pure tone with gentle breath."""
    sig = _harmonics(freq, dur, weights=[1.0, 0.24, 0.07, 0.02], sr=sr)
    return _adsr(sig, attack=0.10, decay=0.08, sustain=0.88, release=0.40, sr=sr)


def _drone_note(freq: float, dur: float, sr: int = SR) -> np.ndarray:
    """Deep sustained drone — very slow attack for seamless backdrop."""
    sig = _harmonics(freq, dur, weights=[1.0, 0.32, 0.10, 0.03], sr=sr)
    return _adsr(sig, attack=1.8, decay=0.6, sustain=0.58, release=2.5, sr=sr)


# ---------------------------------------------------------------------------
# Melody and arrangement
# ---------------------------------------------------------------------------

# Erhu melody: (beat_offset, note, duration_in_beats)
# One 8-bar phrase = 32 beats; loops over the full track duration.
_ERHU_PHRASE: list[tuple[float, str, float]] = [
    ( 0.0, "D4",  3.0),
    ( 3.0, "E4",  1.0),
    ( 4.0, "A3",  2.5),
    ( 6.5, "B3",  1.5),
    ( 8.0, "D4",  2.0),
    (10.0, "E4",  1.0),
    (11.0, "D4",  1.0),
    (12.0, "A3",  4.0),   # long resonant hold — stillness
    (16.0, "B4",  2.5),
    (18.5, "A4",  1.5),
    (20.0, "Fs4", 2.0),
    (22.0, "E4",  1.5),
    (23.5, "D4",  0.5),
    (24.0, "A4",  1.0),
    (25.0, "B4",  1.0),
    (26.0, "A4",  1.0),
    (27.0, "Fs4", 1.0),
    (28.0, "D4",  4.0),   # closing phrase hold
]

_PHRASE_BEATS = 32  # 8 bars

# Guzheng: two alternating bar patterns for gentle rhythmic support
_GUZHENG_PATTERNS: list[list[tuple[float, str, float]]] = [
    [(0.0, "D3", 1.2), (2.0, "A3", 1.0)],   # even bars: root + fifth
    [(0.0, "A3", 1.2), (2.0, "Fs3", 1.0)],  # odd bars:  fifth + third
]

# Dizi: two high sparse phrases that enter from bar 4 onward
_DIZI_PHRASES: list[list[tuple[float, str, float]]] = [
    # starts at beat 16 (bar 4) within each 32-beat phrase
    [(0.0, "D5",  2.5), (3.0, "B4",  1.5), (5.0, "A4",  2.0), (7.5, "Fs4", 0.5)],
    # starts at beat 24 (bar 6)
    [(0.0, "B4",  2.0), (2.5, "A4",  1.5), (4.0, "E4",  2.0), (6.5, "D4",  1.5)],
]


def _place_notes(
    buf: np.ndarray,
    notes: list[tuple[float, str, float]],
    start_beat: float,
    voice_fn,
    gain: float,
    sr: int = SR,
) -> None:
    """Render (beat_offset, note, dur_beats) tuples into buf starting at start_beat."""
    for beat_off, note, dur_b in notes:
        t0 = int((start_beat + beat_off) * BEAT * sr)
        if t0 >= len(buf):
            continue
        dur_s = dur_b * BEAT
        sig = voice_fn(_p(note), dur_s, sr)
        end = min(t0 + len(sig), len(buf))
        buf[t0:end] += gain * sig[:end - t0]


def _erhu_layer(n_beats: float, sr: int = SR) -> np.ndarray:
    buf = np.zeros(int(sr * n_beats * BEAT), dtype=np.float32)
    start = 0.0
    while start < n_beats:
        _place_notes(buf, _ERHU_PHRASE, start, _erhu, gain=1.0, sr=sr)
        start += _PHRASE_BEATS
    return buf


def _guzheng_layer(n_beats: float, sr: int = SR) -> np.ndarray:
    buf = np.zeros(int(sr * n_beats * BEAT), dtype=np.float32)
    n_bars = int(n_beats / 4)
    for bar in range(n_bars):
        pattern = _GUZHENG_PATTERNS[bar % len(_GUZHENG_PATTERNS)]
        _place_notes(buf, pattern, float(bar * 4), _guzheng, gain=0.70, sr=sr)
    return buf


def _dizi_layer(n_beats: float, sr: int = SR) -> np.ndarray:
    buf = np.zeros(int(sr * n_beats * BEAT), dtype=np.float32)
    for phrase_start in range(0, int(n_beats), _PHRASE_BEATS):
        for i, phrase in enumerate(_DIZI_PHRASES):
            beat_offset = phrase_start + 16 + i * 8
            if beat_offset < n_beats:
                _place_notes(buf, phrase, float(beat_offset), _dizi, gain=0.55, sr=sr)
    return buf


def _drone_layer(n_beats: float, sr: int = SR) -> np.ndarray:
    """Continuous tonic (D2) + fifth (A2) drone beneath everything."""
    dur_s = n_beats * BEAT
    n = int(sr * dur_s)
    buf = np.zeros(n, dtype=np.float32)
    seg = _drone_note(_p("D2"), dur_s, sr)
    buf[:len(seg)] += seg
    seg5 = _drone_note(_p("A2"), dur_s, sr)
    buf[:len(seg5)] += 0.45 * seg5
    return buf * 0.38


def _dynamics_envelope(n_samples: int) -> np.ndarray:
    """Soft open → gentle swell → peaceful fade."""
    env = np.ones(n_samples, dtype=np.float32)
    fade_in  = int(n_samples * 0.08)
    fade_out = int(n_samples * 0.10)
    env[:fade_in] = np.linspace(0.0, 1.0, fade_in)
    env[-fade_out:] = np.linspace(1.0, 0.0, fade_out)

    # Subtle mid swell (×1.12 peak around 60% mark)
    s0 = int(n_samples * 0.35)
    s1 = int(n_samples * 0.60)
    end = n_samples - fade_out
    swell = np.ones(n_samples, dtype=np.float32)
    swell[s0:s1]  = np.linspace(1.00, 1.12, s1 - s0)
    swell[s1:end] = np.linspace(1.12, 1.00, end - s1)

    return np.clip(env * swell, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_music(
    output_path: Path,
    duration: float = 32.0,
    mood: str = "peaceful",
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Generate a Chinese traditional-style background music WAV file.

    Uses D major pentatonic with erhu melody, guzheng plucks, dizi flute,
    and a tonic drone for a peaceful, harmonious atmosphere.

    Args:
        output_path: Where to save the .wav file.
        duration:    Length in seconds.
        mood:        Hint for future mood-selection (currently always peaceful).
        progress_cb: Optional progress callback.

    Returns:
        Path to the generated WAV file.
    """
    if progress_cb:
        progress_cb(f"  Composing background music ({duration:.0f}s, {BPM} BPM)...")

    log.info("Generating Chinese traditional background music, %.0f seconds", duration)

    # Round up to whole bars
    n_bars  = max(4, int(np.ceil(duration / BAR)))
    n_beats = float(n_bars * 4)
    dur     = n_beats * BEAT

    erhu    = _erhu_layer(n_beats)
    guzheng = _guzheng_layer(n_beats)
    dizi    = _dizi_layer(n_beats)
    drone   = _drone_layer(n_beats)

    mix = erhu + guzheng + dizi + drone
    mix *= _dynamics_envelope(len(mix))
    mix = _normalize(mix, peak=0.78)
    mix = mix[:int(SR * duration)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit PCM
        wf.setframerate(SR)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())

    if progress_cb:
        size_kb = output_path.stat().st_size // 1024
        progress_cb(f"  ✓ Music generated: {output_path.name} ({size_kb} KB)")

    log.info("Music saved to %s", output_path)
    return output_path
