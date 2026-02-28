import { Show } from "solid-js";
import { jobState, outputPath, jobError, activeJobId } from "../store";

const STATE_LABEL: Record<string, string> = {
  idle: "Ready",
  queued: "Queued…",
  running: "Running…",
  done: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

const STATE_COLOR: Record<string, string> = {
  idle: "var(--muted)",
  queued: "var(--warn)",
  running: "var(--accent-hover)",
  done: "var(--success)",
  failed: "var(--error)",
  cancelled: "var(--muted)",
};

export default function StatusBar() {
  return (
    <div
      style="
        display:flex; align-items:center; gap:12px;
        background:var(--surface); border:1px solid var(--border);
        border-radius:8px; padding:10px 14px; flex-shrink:0;
      "
    >
      {/* State indicator dot */}
      <span
        style={`
          width:8px; height:8px; border-radius:50%;
          background:${STATE_COLOR[jobState()] ?? "var(--muted)"};
          flex-shrink:0;
          ${jobState() === "running" ? "animation:pulse 1.2s infinite;" : ""}
        `}
      />

      <span style={`font-weight:600; font-size:13px; color:${STATE_COLOR[jobState()]};`}>
        {STATE_LABEL[jobState()] ?? jobState()}
      </span>

      <Show when={activeJobId() && jobState() !== "idle"}>
        <span style="font-size:11px; color:var(--muted);">job:{activeJobId()}</span>
      </Show>

      <Show when={jobState() === "done" && outputPath()}>
        <span style="font-size:12px; color:var(--success); margin-left:auto; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          ✅ {outputPath()}
        </span>
      </Show>

      <Show when={jobState() === "failed" && jobError()}>
        <span style="font-size:12px; color:var(--error); margin-left:auto; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          ✗ {jobError()}
        </span>
      </Show>

      <style>{`
        @keyframes pulse {
          0%,100% { opacity:1; }
          50% { opacity:.3; }
        }
      `}</style>
    </div>
  );
}
