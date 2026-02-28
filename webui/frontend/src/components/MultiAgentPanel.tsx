import { Show } from "solid-js";
import { multiAgentOpts, setMultiAgentOpts } from "../store";

export default function MultiAgentPanel() {
  return (
    <div class="card">
      <h3>Multi-Agent Orchestration</h3>

      <label class="toggle-row" style="margin-bottom:8px;">
        <input
          type="checkbox"
          checked={multiAgentOpts.enabled}
          onChange={(e) => setMultiAgentOpts("enabled", e.currentTarget.checked)}
        />
        <span>Enable agent loop</span>
      </label>

      <Show when={multiAgentOpts.enabled}>
        <div style="font-size:11px; color:var(--muted); margin-bottom:10px; line-height:1.5;">
          ProjectManager → VidGen → QualityControl → DevTeam → repeat
        </div>

        <label style="font-size:12px; display:flex; align-items:center; gap:8px;">
          <span style="white-space:nowrap;">Max iterations:</span>
          <input
            type="number"
            min={1}
            max={10}
            value={multiAgentOpts.max_iterations}
            onInput={(e) =>
              setMultiAgentOpts("max_iterations", parseInt(e.currentTarget.value) || 1)
            }
            style="width:60px;"
          />
        </label>

        <div style="margin-top:10px; padding:8px; background:var(--bg); border-radius:5px; font-size:11px; color:var(--muted); line-height:1.6;">
          <strong style="color:var(--text);">Agents:</strong><br />
          📋 <strong>ProjectManager</strong> — Converts prompt to RequirementSpec<br />
          🎬 <strong>VidGen</strong> — Runs full pipeline<br />
          ✅ <strong>QualityControl</strong> — Validates output (resolution, duration, FPS)<br />
          🔧 <strong>DevTeam</strong> — Proposes config fixes if QC fails
        </div>
      </Show>
    </div>
  );
}
