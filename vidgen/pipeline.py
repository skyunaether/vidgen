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
from .musicgen_ai import generate_music_ai
from .scriptgen import Scene, StorySettings, generate_script, parse_markdown_story, parse_user_story, script_to_json
from .story_agent import review_and_refine
from .ttsgen import generate_narration_track, sync_scene_durations_to_narration
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
        self._settings: StorySettings = StorySettings()
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

    def inject_scenes(
        self,
        scenes: list[Scene],
        settings: StorySettings | None = None,
    ) -> None:
        """Pre-load scenes directly, bypassing script generation and story review.

        Call this before ``run()`` to supply a user-provided storyline.
        Stages 1 and 1.5 will be skipped automatically.

        Args:
            scenes:   Pre-built scene list.
            settings: Optional per-story audio settings (voice, music style).
                      Defaults to ``StorySettings()`` if not provided.
        """
        self._scenes = list(scenes)
        if settings is not None:
            self._settings = settings

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
        
        available_models = []
        if self.config.gemini_api_key: available_models.append("veo")
        if self.config.hf_token: available_models.append("hf")
            
        best_practices_path = Path(__file__).parent.parent / "assets" / "ref" / "best_practices.md"
        best_practices = ""
        if best_practices_path.exists():
            with open(best_practices_path, "r", encoding="utf-8") as f:
                best_practices = f.read()

        import concurrent.futures
        import time
        from .utils.gemini_client import submit_video_generation_gemini, check_video_generation_gemini
        from .story_agent import _chat, _extract_json
        
        veo_jobs = {}
        hf_futures = {}
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        
        for scene in video_scenes:
            self._check_cancel()
            if scene.index not in media_paths:
                continue

            img_path = media_paths[scene.index]
            vid_path = tmp / f"scene_{scene.index:03d}.mp4"
            self.progress_cb(f"  Preparing scene {scene.index}...")

            if self.use_placeholders or not available_models:
                generate_placeholder_video(img_path, vid_path, duration=scene.duration)
                self.progress_cb(f"  ✓ Scene {scene.index} animated (placeholder)")
                media_paths[scene.index] = vid_path
                continue

            selected_model = "veo" if "veo" in available_models else "hf"
            enhanced_prompt = scene.visual
            try:
                if self.config.hf_token:
                    system_msg = "You are a Video AI Agent that routes requests to the best model and enhances prompts based on best practices. Reply ONLY with JSON."
                    user_msg = f"AVAILABLE MODELS: {available_models}\nBEST PRACTICES:\n{best_practices}\n\nORIGINAL PROMPT: {scene.visual}\nMEDIA TYPE: {scene.media_type}\n\nReturn JSON with keys 'selected_model' and 'enhanced_prompt'."
                    resp = _chat(system_msg, user_msg, "meta-llama/Llama-3.1-8B-Instruct", self.config.hf_token, max_tokens=500)
                    data = _extract_json(resp)
                    enhanced_prompt = data.get("enhanced_prompt", scene.visual)
                    chosen = data.get("selected_model", selected_model)
                    if chosen in available_models: selected_model = chosen
            except Exception as e:
                log.warning(f"Agent routing failed for scene {scene.index}, using default: {e}")

            if selected_model == "veo":
                try:
                    op_name = submit_video_generation_gemini(enhanced_prompt, self.config, self.progress_cb)
                    veo_jobs[scene.index] = (op_name, vid_path)
                except Exception as e:
                    self.progress_cb(f"  ⚠ Failed to submit Veo job for scene {scene.index}: {e}")
            else:
                def run_hf_gen(img_p, vid_p):
                    generate_video(img_p, vid_p, self.config, self.progress_cb)
                future = executor.submit(run_hf_gen, img_path, vid_path)
                hf_futures[future] = (scene.index, vid_path)

        for future in concurrent.futures.as_completed(hf_futures):
            idx, vid_p = hf_futures[future]
            try:
                future.result()
                self.progress_cb(f"  ✓ Scene {idx} animated (HF)")
                media_paths[idx] = vid_p
            except Exception as e:
                self.progress_cb(f"  ⚠ HF Animation failed for scene {idx}: {e}")

        while veo_jobs:
            self._check_cancel()
            done_keys = []
            for idx, (op_name, vid_p) in veo_jobs.items():
                try:
                    res = check_video_generation_gemini(op_name, vid_p, self.config)
                    if res is not None:
                        self.progress_cb(f"  ✓ Scene {idx} animated (Veo)")
                        media_paths[idx] = res
                        done_keys.append(idx)
                except Exception as e:
                    self.progress_cb(f"  ⚠ Veo Animation failed for scene {idx}: {e}")
                    done_keys.append(idx)
                    
            for k in done_keys:
                del veo_jobs[k]
                
            if veo_jobs:
                time.sleep(5)

        executor.shutdown(wait=True)
        return media_paths

    def step_generate_narration(self) -> str | None:
        """Stage 4/5: Generate narrator voice track for all scenes."""
        self.progress_cb("🎙️ Stage 4/5: Generating narrator voice...")
        self._check_cancel()

        if not self._scenes:
            return None

        s = self._settings
        try:
            tmp = Path(self._tmpdir)
            narration_path = tmp / "narration.wav"
            narrations = [scene.narration for scene in self._scenes]
            durations  = [scene.duration  for scene in self._scenes]
            generate_narration_track(
                narrations, durations, narration_path,
                progress_cb=self.progress_cb,
                voice=s.voice,
                rate=s.voice_rate,
                pitch=s.voice_pitch,
            )
            return str(narration_path)
        except Exception as e:
            self.progress_cb(f"  ⚠ Narration failed: {e} — continuing without narrator")
            log.warning("Narration gen failed: %s", e)
            return None

    def step_generate_music(self, prompt: str) -> str | None:
        """Stage 4.5/5: Generate background music matching the story mood."""
        self.progress_cb("🎵 Stage 4.5/5: Generating background music...")
        self._check_cancel()

        # Skip if user supplied their own music track
        if self.config.bg_music and Path(self.config.bg_music).exists():
            self.progress_cb(f"  Using provided track: {self.config.bg_music}")
            return self.config.bg_music

        # Use per-story music style; if still at the generic default, also
        # check prompt keywords so auto-generated stories get a sensible mood.
        music_style = self._settings.music_style
        if music_style == StorySettings().music_style:
            lower = prompt.lower()
            if any(k in lower for k in ["epic", "fly", "wing", "soar", "hero", "triumph"]):
                music_style = "epic"
            elif any(k in lower for k in ["sad", "dark", "loss", "death", "mourn"]):
                music_style = "melancholic"
            elif any(k in lower for k in ["calm", "peace", "nature", "ocean", "forest"]):
                music_style = "peaceful"

        tmp = Path(self._tmpdir)
        music_path = tmp / "background_music.wav"

        # Try AI music generation first (MusicGen)
        if self.config.use_ai_music and not self.use_placeholders:
            try:
                self.progress_cb("  Using AI music generation (MusicGen)...")
                generate_music_ai(
                    music_path,
                    prompt=music_style,
                    model_id=self.config.music_model,
                    duration=30.0,
                    progress_cb=self.progress_cb,
                )
                return str(music_path)
            except Exception as e:
                self.progress_cb(f"  ⚠ AI music failed: {e} — falling back to procedural")
                log.warning("AI music gen failed, falling back: %s", e)

        # Fallback: procedural synthesis
        try:
            generate_music(music_path, duration=36.0, mood=music_style,
                           progress_cb=self.progress_cb)
            return str(music_path)
        except Exception as e:
            self.progress_cb(f"  ⚠ Music generation failed: {e} — continuing without music")
            log.warning("Music gen failed: %s", e)
            return None

    def step_export_airtable(self, media_paths: dict[int, Path]) -> None:
        """Stage 4.8/5: Export scene data to a CSV for Airtable import."""
        self.progress_cb("📊 Stage 4.8/5: Exporting Airtable spreadsheet...")
        self._check_cancel()

        import csv
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / f"airtable_export_{timestamp}.csv"

        try:
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Airtable-friendly headers
                writer.writerow(["Scene Index", "Media Type", "Duration", "Narration", "Visual Prompt", "Generated Media Path"])
                
                for scene in self._scenes:
                    media_path = str(media_paths.get(scene.index, ""))
                    writer.writerow([
                        scene.index,
                        scene.media_type,
                        scene.duration,
                        scene.narration,
                        scene.visual,
                        media_path
                    ])
            self.progress_cb(f"  ✓ Airtable CSV saved to {csv_path}")
        except Exception as e:
            self.progress_cb(f"  ⚠ Failed to export Airtable CSV: {e}")
            log.warning("Airtable CSV export failed: %s", e)

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
            # Sync scene durations to fit narration (prevents cutting off speech)
            s = self._settings
            sync_scene_durations_to_narration(
                self._scenes, self.progress_cb,
                voice=s.voice, rate=s.voice_rate, pitch=s.voice_pitch,
            )
            self.progress_cb("")
            
            media_paths = self.step_generate_images()
            media_paths = self.step_generate_videos(media_paths)
            narration = self.step_generate_narration()
            bg_music = self.step_generate_music(prompt)
            self.step_export_airtable(media_paths)
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
