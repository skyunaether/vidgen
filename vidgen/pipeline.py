"""Orchestrates the full video generation pipeline."""
from __future__ import annotations

import logging
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from .compiler import compile_video
from .config import Config
from .imagegen import generate_image, generate_placeholder_image
from .musicgen import generate_music
from .scriptgen import Scene, generate_script, parse_markdown_story, parse_user_story, script_to_json
from .story_agent import review_and_refine
from .ttsgen import generate_narration_track
from .videogen import generate_placeholder_video, generate_video

log = logging.getLogger(__name__)


class PipelineCancelled(Exception):
    pass


class Pipeline:
    """Full video generation pipeline with cancellation support."""

    def __init__(
        self,
        config: Config,
        progress_cb: Callable[[str], None] | None = None,
        use_placeholders: bool = False,
    ):
        self.config = config
        self.progress_cb = progress_cb or (lambda msg: None)
        self.use_placeholders = use_placeholders
        self._cancelled = threading.Event()
        self._scenes: list[Scene] = []
        self._tmpdir: str | None = None

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def _check_cancel(self) -> None:
        if self._cancelled.is_set():
            raise PipelineCancelled("Pipeline cancelled by user.")

    @property
    def scenes(self) -> list[Scene]:
        return self._scenes

    def inject_scenes(self, scenes: list[Scene]) -> None:
        """Pre-load scenes directly, bypassing script generation and story review.

        Call this before ``run()`` to supply a user-provided storyline.
        Stages 1 and 1.5 will be skipped automatically.
        """
        self._scenes = list(scenes)

    def step_generate_script(self, prompt: str) -> list[Scene]:
        """Stage 1: Generate scene breakdown."""
        self.progress_cb("📝 Stage 1/5: Generating script...")
        self._check_cancel()

        self._scenes = generate_script(prompt)
        total_dur = sum(s.duration for s in self._scenes)

        self.progress_cb(f"  Generated {len(self._scenes)} scenes, ~{total_dur:.0f}s total")
        for s in self._scenes:
            self.progress_cb(f"  Scene {s.index}: [{s.media_type}] {s.duration}s — {s.narration[:60]}")

        return self._scenes

    def step_review_story(self, prompt: str) -> None:
        """Stage 1.5: AI reviewer–refiner loop to improve the storyline."""
        self.progress_cb("🤖 Stage 1.5/5: Story Reviewer Agent running...")
        self._check_cancel()

        if not self.config.hf_token:
            self.progress_cb("  ⚠ No HF token — skipping story review.")
            return

        if self.use_placeholders:
            self.progress_cb("  ⚠ Test mode — skipping story review.")
            return

        try:
            refined_scenes, final_review = review_and_refine(
                scenes=self._scenes,
                prompt=prompt,
                config=self.config,
                progress_cb=self.progress_cb,
            )
            self._scenes = refined_scenes
            self.progress_cb(
                f"\n  📖 Final storyline (score {final_review.score}/10):"
            )
            for s in self._scenes:
                self.progress_cb(f"  Scene {s.index}: {s.narration[:70]}")
        except Exception as e:
            self.progress_cb(f"  ⚠ Story review failed: {e} — using original storyline")
            log.warning("Story review failed: %s", e)

    def step_generate_images(self) -> dict[int, Path]:
        """Stage 2: Generate images for all scenes."""
        self.progress_cb("🎨 Stage 2/5: Generating images...")
        self._check_cancel()

        tmpdir = tempfile.mkdtemp(prefix="vidgen_")
        self._tmpdir = tmpdir
        tmp = Path(tmpdir)

        media_paths: dict[int, Path] = {}

        for scene in self._scenes:
            self._check_cancel()
            img_path = tmp / f"scene_{scene.index:03d}.png"
            self.progress_cb(f"  Generating image for scene {scene.index}...")

            try:
                if self.use_placeholders or not self.config.hf_token:
                    generate_placeholder_image(scene.visual, img_path)
                    self.progress_cb(f"  ✓ Scene {scene.index} (placeholder)")
                else:
                    generate_image(scene.visual, img_path, self.config, self.progress_cb)
                    self.progress_cb(f"  ✓ Scene {scene.index}")
                media_paths[scene.index] = img_path
            except Exception as e:
                self.progress_cb(f"  ✗ Scene {scene.index} failed: {e}")
                log.error("Image gen failed for scene %d: %s", scene.index, e)
                # Generate placeholder as fallback
                try:
                    generate_placeholder_image(scene.visual, img_path)
                    media_paths[scene.index] = img_path
                    self.progress_cb(f"  ↳ Used placeholder for scene {scene.index}")
                except Exception:
                    pass

        return media_paths

    def step_generate_videos(self, media_paths: dict[int, Path]) -> dict[int, Path]:
        """Stage 3: Animate key scenes (those marked as 'video' type)."""
        video_scenes = [s for s in self._scenes if s.media_type == "video"]
        if not video_scenes:
            self.progress_cb("🎬 Stage 3/5: No video scenes to animate, skipping.")
            return media_paths

        self.progress_cb(f"🎬 Stage 3/5: Animating {len(video_scenes)} scenes...")
        self._check_cancel()

        tmp = Path(self._tmpdir)

        for scene in video_scenes:
            self._check_cancel()
            if scene.index not in media_paths:
                continue

            img_path = media_paths[scene.index]
            vid_path = tmp / f"scene_{scene.index:03d}.mp4"
            self.progress_cb(f"  Animating scene {scene.index}...")

            try:
                if self.use_placeholders or not self.config.hf_token:
                    generate_placeholder_video(img_path, vid_path, duration=scene.duration)
                    self.progress_cb(f"  ✓ Scene {scene.index} animated (placeholder)")
                else:
                    generate_video(img_path, vid_path, self.config, self.progress_cb)
                    self.progress_cb(f"  ✓ Scene {scene.index} animated")
                media_paths[scene.index] = vid_path
            except Exception as e:
                self.progress_cb(f"  ⚠ Animation failed for scene {scene.index}: {e}")
                log.warning("Video gen failed for scene %d, keeping image: %s", scene.index, e)

        return media_paths

    def step_generate_narration(self) -> str | None:
        """Stage 4/5: Generate narrator voice track for all scenes."""
        self.progress_cb("🎙️ Stage 4/5: Generating narrator voice...")
        self._check_cancel()

        if not self._scenes:
            return None

        try:
            tmp = Path(self._tmpdir)
            narration_path = tmp / "narration.wav"
            narrations = [s.narration for s in self._scenes]
            durations = [s.duration for s in self._scenes]
            generate_narration_track(
                narrations, durations, narration_path,
                progress_cb=self.progress_cb,
            )
            return str(narration_path)
        except Exception as e:
            self.progress_cb(f"  ⚠ Narration failed: {e} — continuing without narrator")
            log.warning("Narration gen failed: %s", e)
            return None

    def step_generate_music(self, prompt: str) -> str | None:
        """Stage 3.5: Generate background music matching the story mood."""
        self.progress_cb("🎵 Stage 4.5/5: Generating background music...")
        self._check_cancel()

        # Skip if user supplied their own music track
        if self.config.bg_music and Path(self.config.bg_music).exists():
            self.progress_cb(f"  Using provided track: {self.config.bg_music}")
            return self.config.bg_music

        # Pick mood from prompt keywords
        lower = prompt.lower()
        if any(k in lower for k in ["fly", "wing", "soar", "flight", "sky", "hero", "triumph", "epic"]):
            mood = "epic"
        elif any(k in lower for k in ["sad", "dark", "loss", "death", "mourn"]):
            mood = "melancholic"
        elif any(k in lower for k in ["nature", "ocean", "forest", "calm", "peace"]):
            mood = "ambient"
        else:
            mood = "epic"

        try:
            tmp = Path(self._tmpdir)
            music_path = tmp / "background_music.wav"
            # Generate ~36 seconds (4.5 bars × 4 beats at 72 BPM ≈ loopable)
            generate_music(music_path, duration=36.0, mood=mood,
                           progress_cb=self.progress_cb)
            return str(music_path)
        except Exception as e:
            self.progress_cb(f"  ⚠ Music generation failed: {e} — continuing without music")
            log.warning("Music gen failed: %s", e)
            return None

    def step_compile(
        self,
        media_paths: dict[int, Path],
        bg_music: str | None = None,
        narration: str | None = None,
    ) -> Path:
        """Stage 5: Compile final video."""
        self.progress_cb("🎞️ Stage 5/5: Compiling final video...")
        self._check_cancel()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"vidgen_{timestamp}.mp4"

        compile_video(
            scenes=self._scenes,
            media_paths=media_paths,
            output_path=output_path,
            bg_music=bg_music or self.config.bg_music,
            narration=narration,
            progress_cb=self.progress_cb,
        )

        return output_path

    def run(self, prompt: str) -> Path:
        """Run the complete pipeline end-to-end.

        Returns the path to the final video.
        """
        try:
            if not self._scenes:
                # Normal path: generate script from prompt + AI review
                self.step_generate_script(prompt)
                self.step_review_story(prompt)
            else:
                # User-provided story: skip generation and review
                total_dur = sum(s.duration for s in self._scenes)
                self.progress_cb(
                    f"📖 Using {len(self._scenes)} pre-provided scenes "
                    f"(~{total_dur:.0f}s) — skipping script generation and story review."
                )
                for s in self._scenes:
                    self.progress_cb(
                        f"  Scene {s.index}: [{s.media_type}] {s.duration}s — {s.narration[:60]}"
                    )
            media_paths = self.step_generate_images()
            media_paths = self.step_generate_videos(media_paths)
            narration = self.step_generate_narration()
            bg_music = self.step_generate_music(prompt)
            output = self.step_compile(media_paths, bg_music=bg_music, narration=narration)
            self.progress_cb(f"\n🎉 Done! Video saved to: {output}")
            return output
        except PipelineCancelled:
            self.progress_cb("\n⛔ Pipeline cancelled.")
            raise
        finally:
            if self._tmpdir:
                shutil.rmtree(self._tmpdir, ignore_errors=True)
                self._tmpdir = None
