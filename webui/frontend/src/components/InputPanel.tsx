import { Show } from "solid-js";
import {
  inputMode, setInputMode,
  prompt, setPrompt,
  story, setStory,
  filesPath, setFilesPath,
  testMode, setTestMode,
} from "../store";

const PLACEHOLDER_STORY = `A young inventor dreams of flight | A lone figure gazing at a starry sky | 10 | image
She builds wings from scrap metal | Close-up of hands welding copper joints | 12 | image
The first test flight begins | Aerial shot of a figure soaring over misty mountains | 14 | video`;

export default function InputPanel() {
  return (
    <div class="card">
      <h3>Input</h3>

      {/* Mode selector */}
      <div class="mode-tabs">
        {(["auto", "manual", "files"] as const).map((m) => (
          <button
            class={`mode-tab ${inputMode() === m ? "active" : ""}`}
            onClick={() => setInputMode(m)}
          >
            {m === "auto" ? "Auto" : m === "manual" ? "Manual" : "Files"}
          </button>
        ))}
      </div>

      {/* Auto mode */}
      <Show when={inputMode() === "auto"}>
        <input
          type="text"
          placeholder="Describe your video topic..."
          value={prompt()}
          onInput={(e) => setPrompt(e.currentTarget.value)}
        />
        <p style="font-size:11px; color:var(--muted); margin-top:5px;">
          The AI generates a full script from your topic.
        </p>
      </Show>

      {/* Manual mode */}
      <Show when={inputMode() === "manual"}>
        <textarea
          placeholder={PLACEHOLDER_STORY}
          value={story()}
          onInput={(e) => setStory(e.currentTarget.value)}
          style="min-height:160px;"
        />
        <p style="font-size:11px; color:var(--muted); margin-top:5px;">
          Format: <code>narration | visual | duration_sec | image/video</code>
          <br />Or paste a full Markdown story starting with <code># Title</code>
        </p>
      </Show>

      {/* Files mode */}
      <Show when={inputMode() === "files"}>
        <input
          type="text"
          placeholder="/path/to/stories/*.md"
          value={filesPath()}
          onInput={(e) => setFilesPath(e.currentTarget.value)}
        />
        <p style="font-size:11px; color:var(--muted); margin-top:5px;">
          Path, glob, or directory of Markdown story files.
        </p>
      </Show>

      {/* Test mode toggle */}
      <label class="toggle-row" style="margin-top:10px;">
        <input
          type="checkbox"
          checked={testMode()}
          onChange={(e) => setTestMode(e.currentTarget.checked)}
        />
        <span>
          Test mode <span style="color:var(--muted);">(placeholder images, no API calls)</span>
        </span>
      </label>
    </div>
  );
}
