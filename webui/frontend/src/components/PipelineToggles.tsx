import { For } from "solid-js";
import { pipelineOpts, setPipelineOpts } from "../store";

type StageKey = keyof typeof pipelineOpts;

const STAGES: [StageKey, string, string][] = [
  ["story_review", "Stage 1.5", "Story Review (AI refinement)"],
  ["image_gen",    "Stage 2",   "Image Generation (FLUX / SDXL)"],
  ["video_gen",    "Stage 3",   "Video Animation (Veo / SVD)"],
  ["narration",    "Stage 4",   "Narration (TTS)"],
  ["music_gen",    "Stage 4.5", "Music Generation (MusicGen)"],
  ["compile",      "Stage 5",   "Compile Final Video (FFmpeg)"],
];

export default function PipelineToggles() {
  return (
    <div class="card">
      <h3>Pipeline Stages</h3>
      <For each={STAGES}>
        {([key, stage, label]) => (
          <label class="toggle-row">
            <input
              type="checkbox"
              checked={pipelineOpts[key]}
              onChange={(e) => setPipelineOpts(key, e.currentTarget.checked)}
            />
            <span>
              <span style="color:var(--accent); font-size:11px; font-weight:600; margin-right:6px;">{stage}</span>
              {label}
            </span>
          </label>
        )}
      </For>
    </div>
  );
}
