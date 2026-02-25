"""FFmpeg video compilation – Ken Burns, transitions, text overlays, stitching."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from .config import CROSSFADE_DURATION, FPS, HEIGHT, WIDTH, KB_OVERSCAN, TRANSITION_TYPES
from .scriptgen import Scene

log = logging.getLogger(__name__)


def _check_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found in PATH. Please install ffmpeg.")


def _has_drawtext() -> bool:
    """Return True if ffmpeg was compiled with the drawtext filter."""
    result = subprocess.run(
        ["ffmpeg", "-filters"],
        capture_output=True,
        timeout=10,
    )
    return b"drawtext" in result.stdout or b"drawtext" in result.stderr


def _pil_burn_subtitle(image_path: Path, text: str, output_path: Path) -> Path:
    """Burn subtitle text onto an image.

    Large readable text filling 80% of frame width, with a dark gradient
    backdrop and multi-layer shadow for cinematic readability.
    """
    import sys
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    draw = ImageDraw.Draw(img)

    # Font size: scale to image height so text is clearly readable
    font_size = max(36, h // 18)
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    # Try platform-appropriate bold fonts
    candidate_fonts = []
    if sys.platform == "win32":
        candidate_fonts = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
    else:
        candidate_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    for font_path in candidate_fonts:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except OSError:
            pass
    else:
        font = ImageFont.load_default()

    # Word-wrap text to fit 80% of frame width
    margin = int(w * 0.10)
    max_width = w - margin * 2
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        test = f"{cur} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)

    line_h = int(font_size * 1.35)
    total_text_h = len(lines) * line_h
    pad_v = int(font_size * 0.6)
    bar_top = h - int(h * 0.22) - total_text_h // 2 - pad_v
    bar_bottom = bar_top + total_text_h + pad_v * 2

    # Dark gradient backdrop (darker at centre, fades at edges)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bar_draw = ImageDraw.Draw(overlay)
    bar_draw.rounded_rectangle(
        [margin // 2, bar_top, w - margin // 2, bar_bottom],
        radius=int(font_size * 0.4),
        fill=(0, 0, 0, 180),
    )
    # Soften edges of the backdrop
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Draw each line centred with multi-layer shadow for depth
    text_y = bar_top + pad_v
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        # Outer shadow (soft)
        draw.text((x + 4, text_y + 4), line, font=font, fill=(0, 0, 0, 140))
        # Inner shadow (crisp)
        draw.text((x + 2, text_y + 2), line, font=font, fill=(0, 0, 0, 220))
        # Main text
        draw.text((x, text_y), line, font=font, fill=(255, 255, 255, 255))
        text_y += line_h

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "PNG")
    return output_path


def _kb_pattern(scene_index: int, frames: int) -> str:
    """Return a zoompan expression string for a Ken Burns motion pattern.

    Cycles through 8 distinct patterns based on scene_index so adjacent
    scenes always have different camera movements.
    """
    # Helper: on/d produces 0→1 linear ramp over the scene duration
    # All expressions use ffmpeg zoompan variables: on (frame number), iw, ih, zoom
    patterns = [
        # 0 — Zoom in + drift right
        (
            "z='1.0+on/{d}*0.15'"
            ":x='(iw-iw/zoom)*on/{d}'"
            ":y='(ih-ih/zoom)/2'"
        ),
        # 1 — Zoom in + drift left
        (
            "z='1.0+on/{d}*0.15'"
            ":x='(iw-iw/zoom)*(1-on/{d})'"
            ":y='(ih-ih/zoom)/2'"
        ),
        # 2 — Zoom out (reveal): start zoomed-in, pull back
        (
            "z='1.20-on/{d}*0.18'"
            ":x='(iw-iw/zoom)/2'"
            ":y='(ih-ih/zoom)/2'"
        ),
        # 3 — Pan up (tilt up): static zoom, bottom-to-top
        (
            "z='1.12'"
            ":x='(iw-iw/zoom)/2'"
            ":y='(ih-ih/zoom)*(1-on/{d})'"
        ),
        # 4 — Pan down (tilt down): static zoom, top-to-bottom
        (
            "z='1.12'"
            ":x='(iw-iw/zoom)/2'"
            ":y='(ih-ih/zoom)*on/{d}'"
        ),
        # 5 — Diagonal drift (top-left to bottom-right) + gentle zoom
        (
            "z='1.0+on/{d}*0.10'"
            ":x='(iw-iw/zoom)*on/{d}'"
            ":y='(ih-ih/zoom)*on/{d}'"
        ),
        # 6 — Slow push in (centre focus, dramatic)
        (
            "z='1.0+on/{d}*0.12'"
            ":x='(iw-iw/zoom)/2'"
            ":y='(ih-ih/zoom)/2'"
        ),
        # 7 — Pull back + slight leftward drift
        (
            "z='1.15-on/{d}*0.13'"
            ":x='(iw-iw/zoom)*(0.6-on/{d}*0.2)'"
            ":y='(ih-ih/zoom)/2'"
        ),
    ]
    pat = patterns[scene_index % len(patterns)]
    return pat.format(d=frames)


def _scene_to_clip(
    scene: Scene,
    media_path: Path,
    clip_path: Path,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Convert a scene's media (image or video) into a standardized clip.

    For images: burns subtitle via PIL then applies Ken Burns zoom.
    For videos: scales/pads and trims to scene duration.
    """
    dur = scene.duration
    is_video = media_path.suffix.lower() in (".mp4", ".webm", ".avi", ".mov")

    # --- Subtitle burn-in ---
    # For images: burn narration text using PIL (works regardless of ffmpeg build).
    # For videos: use drawtext if available, otherwise skip (rare path).
    if not is_video:
        subtitled_path = clip_path.parent / f"sub_{media_path.name}"
        try:
            _pil_burn_subtitle(media_path, scene.narration, subtitled_path)
            input_media = subtitled_path
        except Exception as e:
            log.warning("PIL subtitle failed for scene %d: %s", scene.index, e)
            input_media = media_path
    else:
        input_media = media_path

    if is_video:
        vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"setsar=1"
        )
        if _has_drawtext():
            narration = scene.narration.replace("'", "'\\''").replace(":", "\\:")
            vf += (
                f",drawtext=text='{narration}'"
                f":fontsize=42:fontcolor=white"
                f":shadowcolor=black:shadowx=3:shadowy=3"
                f":x=(w-text_w)/2:y=h-h/4"
                f":font=DejaVu Sans"
            )
        input_args = ["-i", str(input_media)]
        time_args = ["-t", str(dur)]
    else:
        # Image – Varied Ken Burns (zoom + pan, pattern rotated per scene)
        frames = int(dur * FPS)
        overscan_w = int(WIDTH * KB_OVERSCAN)
        overscan_h = int(HEIGHT * KB_OVERSCAN)
        zp_expr = _kb_pattern(scene.index, frames)
        vf = (
            f"scale={overscan_w}x{overscan_h},"
            f"zoompan={zp_expr}:d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
        )
        input_args = ["-loop", "1", "-i", str(input_media)]
        time_args = ["-t", str(dur)]

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        *time_args,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-an",
        str(clip_path),
    ]

    if progress_cb:
        progress_cb(f"  Encoding scene {scene.index}: {clip_path.name}")
    log.info("Running ffmpeg for scene %d", scene.index)
    log.debug("CMD: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")[-500:]
        log.warning("ffmpeg failed for scene %d, trying simple scale: %s", scene.index, stderr)
        if progress_cb:
            progress_cb(f"  ⚠ Ken Burns failed for scene {scene.index}, using simple scale")
        fallback_vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        )
        if is_video:
            fb_input = ["-i", str(input_media)]
        else:
            fb_input = ["-loop", "1", "-i", str(input_media)]
        fb_cmd = [
            "ffmpeg", "-y",
            *fb_input,
            "-t", str(dur),
            "-vf", fallback_vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            str(clip_path),
        ]
        result2 = subprocess.run(fb_cmd, capture_output=True, timeout=300)
        if result2.returncode != 0:
            stderr2 = result2.stderr.decode(errors="replace")[-500:]
            raise RuntimeError(f"ffmpeg fallback failed for scene {scene.index}: {stderr2}")

    return clip_path


def compile_video(
    scenes: list[Scene],
    media_paths: dict[int, Path],  # scene.index -> media file
    output_path: Path,
    bg_music: str | None = None,
    narration: str | None = None,
    progress_cb: Callable[[str], None] | None = None,
) -> Path:
    """Compile all scenes into a final video with transitions and audio.

    Args:
        scenes: List of Scene objects.
        media_paths: Mapping of scene index to generated media file.
        output_path: Final output MP4 path.
        bg_music: Optional path to background music file.
        narration: Optional path to narrator voice WAV file.
        progress_cb: Progress callback.

    Returns:
        Path to the compiled video.
    """
    _check_ffmpeg()

    tmpdir = tempfile.mkdtemp(prefix="vidgen_compile_")
    tmp = Path(tmpdir)

    try:
        # Step 1: Create individual clips
        clip_paths: list[Path] = []
        for scene in scenes:
            if scene.index not in media_paths:
                if progress_cb:
                    progress_cb(f"  ⚠ Skipping scene {scene.index} (no media)")
                continue

            clip_path = tmp / f"clip_{scene.index:03d}.mp4"
            _scene_to_clip(scene, media_paths[scene.index], clip_path, progress_cb)
            clip_paths.append(clip_path)

        if not clip_paths:
            raise RuntimeError("No clips were generated.")

        # Step 2: Concatenate with crossfade transitions
        if progress_cb:
            progress_cb("Applying transitions and stitching clips...")

        if len(clip_paths) == 1:
            shutil.copy2(clip_paths[0], tmp / "merged.mp4")
        else:
            _concat_with_xfade(clip_paths, tmp / "merged.mp4", scenes, progress_cb)

        merged = tmp / "merged.mp4"

        # Step 3: Extend last frame to cover any duration lost through crossfades.
        # Crossfades shorten the video by (N-1)*fade_dur; the narration track is
        # built on the full un-faded durations, so we freeze the last frame to
        # close the gap and prevent the last scene from being cut short.
        narration_path = Path(narration) if narration and Path(narration).exists() else None
        if narration_path:
            narr_dur = _get_duration(narration_path)
            vid_dur  = _get_duration(merged)
            if narr_dur > vid_dur + 0.1:
                extended = tmp / "merged_extended.mp4"
                if progress_cb:
                    progress_cb(
                        f"  Extending last frame by {narr_dur - vid_dur:.1f}s "
                        f"to match narration ({vid_dur:.1f}s → {narr_dur:.1f}s)..."
                    )
                _freeze_extend_video(merged, extended, narr_dur)
                merged = extended

        # Step 4: Mix audio (narrator + music)
        music_path = Path(bg_music) if bg_music and Path(bg_music).exists() else None

        if narration_path:
            if progress_cb:
                progress_cb("Mixing narrator voice with background music..." if music_path else "Adding narrator voice...")
            _mix_audio_tracks(merged, narration_path, music_path, tmp / "final.mp4")
        elif music_path:
            if progress_cb:
                progress_cb("Adding background music...")
            _add_audio(merged, music_path, tmp / "final.mp4")
        else:
            _add_silent_audio(merged, tmp / "final.mp4")

        final = tmp / "final.mp4"

        # Copy to output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(final, output_path)

        if progress_cb:
            progress_cb(f"✅ Video saved to {output_path}")

        return output_path

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _get_duration(clip_path: Path) -> float:
    """Get actual duration of a video or audio file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(clip_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    return 10.0  # fallback


def _freeze_extend_video(video: Path, output: Path, target_dur: float) -> None:
    """Extend video to target_dur by freezing (looping) the last frame.

    Used to compensate for the cumulative time lost by crossfade transitions so
    that the merged video duration matches the narration track duration, preventing
    the last scene from being cut short when audio is mixed.
    """
    current_dur = _get_duration(video)
    extra = target_dur - current_dur
    if extra <= 0.05:          # already long enough
        shutil.copy2(video, output)
        return

    log.debug("Freeze-extending video by %.2fs (%.2fs → %.2fs)", extra, current_dur, target_dur)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-vf", f"tpad=stop_mode=clone:stop_duration={extra:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        log.warning("freeze-extend failed, copying original: %s",
                    result.stderr.decode(errors="replace")[-300:])
        shutil.copy2(video, output)


def _concat_with_xfade(
    clip_paths: list[Path],
    output: Path,
    scenes: list[Scene],
    progress_cb: Callable[[str], None] | None = None,
) -> None:
    """Concatenate clips with crossfade transitions using xfade filter."""
    n = len(clip_paths)
    if n < 2:
        shutil.copy2(clip_paths[0], output)
        return

    inputs = []
    for p in clip_paths:
        inputs.extend(["-i", str(p)])

    fade_dur = CROSSFADE_DURATION

    # Probe actual clip durations
    clip_durations = [_get_duration(p) for p in clip_paths]
    if progress_cb:
        total = sum(clip_durations) - fade_dur * (n - 1)
        progress_cb(f"  Total clip durations: {sum(clip_durations):.1f}s, estimated output: {total:.1f}s")

    # Calculate xfade offsets relative to the output stream
    # offset[0] = dur[0] - fade_dur  (start of first transition)
    # After xfade[0], output duration = dur[0] + dur[1] - fade_dur
    # offset[1] = (dur[0] + dur[1] - fade_dur) - fade_dur = dur[0] + dur[1] - 2*fade_dur
    # In general: offset[i] = sum(dur[0..i]) - (i+1)*fade_dur  BUT
    # for chained xfade, each offset is relative to the output of the previous xfade
    # offset[0] = dur[0] - fade_dur
    # output_after_0 = dur[0] + dur[1] - fade_dur
    # offset[1] = output_after_0 - fade_dur = dur[0] + dur[1] - 2*fade_dur
    # etc.
    offsets: list[float] = []
    running_output_dur = clip_durations[0]
    for i in range(n - 1):
        offset = running_output_dur - fade_dur
        offsets.append(max(0.1, offset))
        # After this xfade, output duration grows by (next clip dur - fade)
        if i + 1 < len(clip_durations):
            running_output_dur = offset + clip_durations[i + 1]

    # Build filter chain with varied transition types
    if n == 2:
        tr = TRANSITION_TYPES[0 % len(TRANSITION_TYPES)]
        filter_str = f"[0:v][1:v]xfade=transition={tr}:duration={fade_dur}:offset={offsets[0]},format=yuv420p[v]"
    else:
        parts = []
        prev = "[0:v]"
        for i in range(n - 1):
            tr = TRANSITION_TYPES[i % len(TRANSITION_TYPES)]
            next_in = f"[{i+1}:v]"
            if i == n - 2:
                parts.append(
                    f"{prev}{next_in}xfade=transition={tr}:duration={fade_dur}:offset={offsets[i]},format=yuv420p[v]"
                )
            else:
                out_label = f"[xf{i}]"
                parts.append(
                    f"{prev}{next_in}xfade=transition={tr}:duration={fade_dur}:offset={offsets[i]}{out_label}"
                )
                prev = out_label
        filter_str = ";".join(parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(output),
    ]

    log.debug("Concat CMD: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")[-500:]
        log.warning("xfade concat failed, falling back to simple concat: %s", stderr)
        _simple_concat(clip_paths, output)


def _simple_concat(clip_paths: list[Path], output: Path) -> None:
    """Fallback: simple concatenation without transitions."""
    list_file = output.parent / "concat_list.txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(output),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=600)


def _add_audio(video: Path, audio: Path, output: Path) -> None:
    """Mix background-only audio into video (loops if shorter than video)."""
    vid_dur = _get_duration(video)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-i", str(audio),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-filter_complex",
        f"[1:a]aloop=loop=-1:size=2e+09,volume=0.18,atrim=0:{vid_dur:.3f}[a]",
        "-map", "0:v", "-map", "[a]",
        "-t", f"{vid_dur:.3f}",
        str(output),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=300)


def _mix_audio_tracks(
    video: Path,
    narration: Path,
    music: Path | None,
    output: Path,
) -> None:
    """Mix video with narrator voice and optional background music.

    Narrator is full volume; music is ducked to 15% so the voice is clear.
    Music loops if shorter than the video.
    """
    # Get video duration to trim/pad audio precisely — no -shortest needed
    # because we already extended the video to match narration length.
    vid_dur = _get_duration(video)

    if music is None:
        # Narrator only — no background music
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(narration),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-filter_complex",
            f"[1:a]volume=1.0,atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS[a]",
            "-map", "0:v", "-map", "[a]",
            "-t", f"{vid_dur:.3f}",
            str(output),
        ]
    else:
        # Narrator (1.0) + looped music (0.15) mixed together
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(narration),
            "-i", str(music),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-filter_complex", (
                f"[1:a]volume=1.0,atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS[narrator];"
                f"[2:a]aloop=loop=-1:size=2e+09,volume=0.15,atrim=0:{vid_dur:.3f}[music];"
                "[narrator][music]amix=inputs=2:duration=first:dropout_transition=2[a]"
            ),
            "-map", "0:v", "-map", "[a]",
            "-t", f"{vid_dur:.3f}",
            str(output),
        ]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        log.warning("Audio mix failed: %s", result.stderr.decode(errors="replace")[-400:])
        # Fallback: narrator only, no music
        cmd2 = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(narration),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output),
        ]
        subprocess.run(cmd2, capture_output=True, check=True, timeout=300)


def _add_silent_audio(video: Path, output: Path) -> None:
    """Add a silent audio track for player compatibility."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        # If silent audio fails, just copy video as-is
        shutil.copy2(video, output)
