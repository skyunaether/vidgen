import { createEffect, onMount, Show } from "solid-js";
import {
  activeTab, setActiveTab,
  config, setConfig,
  pipelineOpts,
  multiAgentOpts,
  inputMode, prompt, story, filesPath, testMode,
  jobState, setJobState,
  setActiveJobId,
  setOutputPath, setJobError,
  appendLog, clearLogs, logs,
} from "./store";
import { fetchConfig, submitJob, cancelJob, streamJob } from "./api";
import type { SseStatusMsg } from "./api";

import InputPanel from "./components/InputPanel";
import PipelineToggles from "./components/PipelineToggles";
import MultiAgentPanel from "./components/MultiAgentPanel";
import ConfigPanel from "./components/ConfigPanel";
import LogPanel from "./components/LogPanel";
import StatusBar from "./components/StatusBar";
import OutputPanel from "./components/OutputPanel";

// ── Styles ────────────────────────────────────────────────────────────────────
const css = `
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2d3148;
    --accent: #6366f1;
    --accent-hover: #818cf8;
    --success: #22c55e;
    --warn: #f59e0b;
    --error: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
    --green: #4ade80;
  }
  body { background: var(--bg); color: var(--text); }

  .app { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

  /* ── Tab bar ── */
  .tabs { display: flex; gap: 2px; padding: 8px 16px 0; background: var(--surface); border-bottom: 1px solid var(--border); }
  .tab { padding: 8px 20px; border-radius: 6px 6px 0 0; cursor: pointer; font-weight: 500; color: var(--muted); transition: color .15s; border: none; background: transparent; }
  .tab:hover { color: var(--text); }
  .tab.active { background: var(--bg); color: var(--accent); }

  /* ── Main layout ── */
  .main { display: flex; flex: 1; overflow: hidden; }
  .sidebar { width: 320px; flex-shrink: 0; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; border-right: 1px solid var(--border); }
  .content { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 16px; gap: 12px; }

  /* ── Cards ── */
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
  .card h3 { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 10px; }

  /* ── Execute button ── */
  .btn-execute {
    width: 100%; padding: 12px; border-radius: 8px; border: none; cursor: pointer;
    font-size: 15px; font-weight: 700; letter-spacing: .04em;
    background: var(--accent); color: #fff;
    transition: background .15s, transform .1s;
  }
  .btn-execute:hover:not(:disabled) { background: var(--accent-hover); transform: translateY(-1px); }
  .btn-execute:disabled { opacity: .5; cursor: not-allowed; }
  .btn-execute.running { background: var(--error); }

  /* ── Inputs ── */
  input[type=text], input[type=number], textarea, select {
    background: var(--bg); color: var(--text); border: 1px solid var(--border);
    border-radius: 6px; padding: 7px 10px; font-size: 13px; width: 100%;
    font-family: inherit; outline: none; transition: border-color .15s;
  }
  input:focus, textarea:focus, select:focus { border-color: var(--accent); }
  textarea { resize: vertical; min-height: 100px; font-family: 'Courier New', monospace; }

  /* ── Checkboxes/Labels ── */
  .toggle-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 13px; cursor: pointer; }
  .toggle-row input[type=checkbox] { width: 15px; height: 15px; cursor: pointer; accent-color: var(--accent); }

  /* ── Mode tabs ── */
  .mode-tabs { display: flex; gap: 4px; margin-bottom: 10px; }
  .mode-tab { flex: 1; padding: 6px; border: 1px solid var(--border); border-radius: 5px; background: var(--bg); color: var(--muted); cursor: pointer; font-size: 12px; font-weight: 600; text-align: center; transition: all .15s; }
  .mode-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }
`;

export default function App() {
  let cleanupSse: (() => void) | null = null;

  onMount(async () => {
    try {
      const cfg = await fetchConfig();
      setConfig(cfg as any);
    } catch (e) {
      console.warn("Could not load config:", e);
    }
  });

  async function handleExecute() {
    if (jobState() === "running") {
      // Cancel
      const id = (window as any).__activeJobId as string;
      if (id) await cancelJob(id);
      setJobState("cancelled");
      cleanupSse?.();
      return;
    }

    clearLogs();
    setJobError(null);
    setOutputPath(null);
    setJobState("queued");

    try {
      const jobId = await submitJob({
        mode: inputMode(),
        prompt: prompt(),
        story: story(),
        files_path: filesPath(),
        use_test_mode: testMode(),
        pipeline: { ...pipelineOpts },
        multi_agent: { ...multiAgentOpts },
        use_ai_music: null,
        use_ai_tts: null,
      });

      setActiveJobId(jobId);
      (window as any).__activeJobId = jobId;
      setJobState("running");

      cleanupSse = streamJob(
        jobId,
        (text) => appendLog(text),
        (msg: SseStatusMsg) => {
          if (msg.state === "done") {
            setJobState("done");
            setOutputPath(msg.output ?? null);
          } else {
            setJobState(msg.state === "failed" ? "failed" : "cancelled");
            setJobError(msg.error ?? null);
          }
        }
      );
    } catch (e: any) {
      setJobState("failed");
      setJobError(String(e));
      appendLog(`Error: ${e}`);
    }
  }

  const isRunning = () => jobState() === "running" || jobState() === "queued";

  return (
    <>
      <style>{css}</style>
      <div class="app">
        {/* Tab bar */}
        <div class="tabs">
          {(["dashboard", "config", "outputs"] as const).map((t) => (
            <button
              class={`tab ${activeTab() === t ? "active" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t === "dashboard" ? "Dashboard" : t === "config" ? "Settings" : "Outputs"}
            </button>
          ))}
        </div>

        {/* Dashboard */}
        <Show when={activeTab() === "dashboard"}>
          <div class="main">
            {/* Left sidebar: controls */}
            <div class="sidebar">
              <InputPanel />
              <PipelineToggles />
              <MultiAgentPanel />

              {/* Execute / Cancel button */}
              <button
                class={`btn-execute ${isRunning() ? "running" : ""}`}
                onClick={handleExecute}
              >
                {isRunning() ? "⛔ Cancel" : "▶ Execute"}
              </button>
            </div>

            {/* Right: log output */}
            <div class="content">
              <StatusBar />
              <LogPanel />
            </div>
          </div>
        </Show>

        {/* Config */}
        <Show when={activeTab() === "config"}>
          <div style="padding:16px; overflow-y:auto; flex:1;">
            <ConfigPanel />
          </div>
        </Show>

        {/* Outputs */}
        <Show when={activeTab() === "outputs"}>
          <div style="padding:16px; overflow-y:auto; flex:1;">
            <OutputPanel />
          </div>
        </Show>
      </div>
    </>
  );
}
