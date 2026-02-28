import { For, createEffect } from "solid-js";
import { logs, clearLogs } from "../store";

/**
 * Terminal-like log panel.
 * SolidJS <For> is key-diffed — only the NEW <p> is added to the DOM per log line.
 * No full-list re-render, no Virtual DOM diffing. O(1) DOM patch per message.
 */
export default function LogPanel() {
  let containerRef: HTMLDivElement | undefined;

  // Auto-scroll to bottom on new log lines
  createEffect(() => {
    logs(); // subscribe
    if (containerRef) {
      containerRef.scrollTop = containerRef.scrollHeight;
    }
  });

  function colorize(line: string): string {
    // Apply ANSI-style coloring via inline styles (handled by innerHTML is risky;
    // we use a simple span wrapping approach instead)
    return line;
  }

  function lineColor(line: string): string {
    if (/✅|✓|approved|Done!|🎉/.test(line)) return "var(--success)";
    if (/⚠|✗|failed|skipping|Warning/.test(line)) return "var(--warn)";
    if (/Error|error|⛔|FAIL/.test(line)) return "var(--error)";
    if (/Stage \d/.test(line)) return "var(--accent-hover)";
    if (/^\s*(Reviewer|Refiner|Iteration|Score)/.test(line)) return "#94a3b8";
    return "var(--green)";
  }

  return (
    <div style="display:flex; flex-direction:column; flex:1; min-height:0;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-size:12px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.06em;">
          Log Output
        </span>
        <button
          onClick={clearLogs}
          style="font-size:11px; color:var(--muted); background:none; border:1px solid var(--border); border-radius:4px; padding:2px 8px; cursor:pointer;"
        >
          Clear
        </button>
      </div>

      <div
        ref={containerRef}
        style="
          flex: 1;
          background: #0a0c12;
          border: 1px solid var(--border);
          border-radius: 8px;
          padding: 12px 14px;
          overflow-y: auto;
          font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
          font-size: 12.5px;
          line-height: 1.6;
          min-height: 300px;
        "
      >
        <For each={logs()} fallback={
          <p style="color:var(--muted); font-style:italic;">Waiting for output...</p>
        }>
          {(line) => (
            <p style={`color:${lineColor(line)}; margin:0; white-space:pre-wrap; word-break:break-all;`}>
              {line}
            </p>
          )}
        </For>
      </div>
    </div>
  );
}
