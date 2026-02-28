import { config, setConfig } from "../store";
import { saveConfig } from "../api";
import { createSignal } from "solid-js";

export default function ConfigPanel() {
  const [saved, setSaved] = createSignal(false);
  const [err, setErr] = createSignal("");

  async function handleSave() {
    setErr("");
    try {
      await saveConfig({ ...config });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setErr(String(e));
    }
  }

  const field = (
    label: string,
    key: keyof typeof config,
    opts: { type?: string; placeholder?: string } = {}
  ) => (
    <div style="margin-bottom:12px;">
      <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">
        {label}
      </label>
      <input
        type={opts.type ?? "text"}
        placeholder={opts.placeholder ?? ""}
        value={config[key] as string}
        onInput={(e) => setConfig(key as any, e.currentTarget.value as any)}
      />
    </div>
  );

  return (
    <div style="max-width:600px;">
      <div class="card" style="margin-bottom:12px;">
        <h3>API Keys</h3>
        {field("HuggingFace Token", "hf_token", { type: "password", placeholder: "hf_..." })}
        {field("Google Gemini API Key", "gemini_api_key", { type: "password", placeholder: "AIza..." })}
      </div>

      <div class="card" style="margin-bottom:12px;">
        <h3>Output</h3>
        {field("Output Directory", "output_dir", { placeholder: "output" })}
      </div>

      <div class="card" style="margin-bottom:12px;">
        <h3>Audio Models</h3>

        <label class="toggle-row" style="margin-bottom:10px;">
          <input
            type="checkbox"
            checked={config.use_ai_music}
            onChange={(e) => setConfig("use_ai_music", e.currentTarget.checked)}
          />
          <span>Use AI Music Generation (MusicGen)</span>
        </label>

        <div style="margin-bottom:12px;">
          <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">
            Music Model
          </label>
          <select
            value={config.music_model}
            onChange={(e) => setConfig("music_model", e.currentTarget.value)}
          >
            <option value="facebook/musicgen-small">MusicGen Small (fast)</option>
            <option value="facebook/musicgen-medium">MusicGen Medium</option>
            <option value="facebook/musicgen-large">MusicGen Large (slow)</option>
          </select>
        </div>

        <label class="toggle-row" style="margin-bottom:10px;">
          <input
            type="checkbox"
            checked={config.use_ai_tts}
            onChange={(e) => setConfig("use_ai_tts", e.currentTarget.checked)}
          />
          <span>Use Parler-TTS <span style="color:var(--muted);">(default: Edge TTS)</span></span>
        </label>

        <div>
          <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">
            TTS Model
          </label>
          <select
            value={config.tts_model}
            onChange={(e) => setConfig("tts_model", e.currentTarget.value)}
          >
            <option value="parler-tts/parler-tts-mini-v1">Parler-TTS Mini v1</option>
            <option value="parler-tts/parler-tts-large-v1">Parler-TTS Large v1</option>
          </select>
        </div>
      </div>

      <button
        class="btn-execute"
        style="max-width:200px;"
        onClick={handleSave}
      >
        {saved() ? "✓ Saved!" : "Save Settings"}
      </button>
      {err() && <p style="color:var(--error); font-size:12px; margin-top:8px;">{err()}</p>}
    </div>
  );
}
