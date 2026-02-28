/**
 * Global reactive store using SolidJS fine-grained signals.
 * No Virtual DOM — each signal update patches only the affected DOM nodes.
 */
import { createSignal } from "solid-js";
import { createStore } from "solid-js/store";

// ── Config ────────────────────────────────────────────────────────────────────
export const [config, setConfig] = createStore({
  hf_token: "",
  gemini_api_key: "",
  output_dir: "output",
  use_ai_music: true,
  use_ai_tts: false,
  music_model: "facebook/musicgen-small",
  tts_model: "parler-tts/parler-tts-mini-v1",
});

// ── Pipeline stage toggles ─────────────────────────────────────────────────
export const [pipelineOpts, setPipelineOpts] = createStore({
  story_review: true,
  image_gen: true,
  video_gen: true,
  narration: true,
  music_gen: true,
  compile: true,
});

// ── Multi-agent options ────────────────────────────────────────────────────
export const [multiAgentOpts, setMultiAgentOpts] = createStore({
  enabled: false,
  max_iterations: 3,
});

// ── Input state ────────────────────────────────────────────────────────────
export type InputMode = "auto" | "manual" | "files";
export const [inputMode, setInputMode] = createSignal<InputMode>("auto");
export const [prompt, setPrompt] = createSignal("");
export const [story, setStory] = createSignal("");
export const [filesPath, setFilesPath] = createSignal("");
export const [testMode, setTestMode] = createSignal(false);

// ── Job state ─────────────────────────────────────────────────────────────
export type JobState = "idle" | "queued" | "running" | "done" | "failed" | "cancelled";
export const [jobState, setJobState] = createSignal<JobState>("idle");
export const [activeJobId, setActiveJobId] = createSignal<string | null>(null);
export const [outputPath, setOutputPath] = createSignal<string | null>(null);
export const [jobError, setJobError] = createSignal<string | null>(null);

// ── Log lines ─────────────────────────────────────────────────────────────
export const [logs, setLogs] = createSignal<string[]>([]);

export function appendLog(line: string): void {
  setLogs((prev) => [...prev, line]);
}

export function clearLogs(): void {
  setLogs([]);
}

// ── Navigation ────────────────────────────────────────────────────────────
export type Tab = "dashboard" | "config" | "outputs";
export const [activeTab, setActiveTab] = createSignal<Tab>("dashboard");

// ── Agent iteration status (multi-agent mode) ─────────────────────────────
export interface AgentStatus {
  agent: string;
  state: "waiting" | "running" | "done" | "failed";
  iteration: number;
}
export const [agentStatuses, setAgentStatuses] = createSignal<AgentStatus[]>([]);
