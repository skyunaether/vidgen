/**
 * Typed API client — REST + SSE.
 */

const BASE = "";  // proxied by Vite dev server to http://localhost:8000

// ── Config ────────────────────────────────────────────────────────────────

export interface ConfigPayload {
  hf_token: string;
  gemini_api_key: string;
  output_dir: string;
  use_ai_music: boolean;
  use_ai_tts: boolean;
  music_model: string;
  tts_model: string;
}

export async function fetchConfig(): Promise<ConfigPayload> {
  const r = await fetch(`${BASE}/api/config`);
  if (!r.ok) throw new Error(`GET /api/config: ${r.status}`);
  return r.json();
}

export async function saveConfig(payload: ConfigPayload): Promise<void> {
  const r = await fetch(`${BASE}/api/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`POST /api/config: ${r.status}`);
}

// ── Jobs ──────────────────────────────────────────────────────────────────

export interface ExecuteRequest {
  mode: "auto" | "manual" | "files";
  prompt: string;
  story: string;
  files_path: string;
  use_test_mode: boolean;
  pipeline: {
    story_review: boolean;
    image_gen: boolean;
    video_gen: boolean;
    narration: boolean;
    music_gen: boolean;
    compile: boolean;
  };
  multi_agent: {
    enabled: boolean;
    max_iterations: number;
  };
  use_ai_music: boolean | null;
  use_ai_tts: boolean | null;
}

export async function submitJob(req: ExecuteRequest): Promise<string> {
  const r = await fetch(`${BASE}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`POST /api/jobs: ${r.status} — ${text}`);
  }
  const { job_id } = await r.json();
  return job_id as string;
}

export async function cancelJob(jobId: string): Promise<void> {
  await fetch(`${BASE}/api/jobs/${jobId}/cancel`, { method: "POST" });
}

// ── SSE log stream ─────────────────────────────────────────────────────────

export interface SseLogMsg {
  type: "log";
  text: string;
  ts: number;
}

export interface SseStatusMsg {
  type: "status";
  state: "done" | "failed" | "cancelled";
  output?: string;
  error?: string;
}

export type SseMsg = SseLogMsg | SseStatusMsg;

/**
 * Open an SSE connection for a job. Returns a cleanup function.
 */
export function streamJob(
  jobId: string,
  onLog: (text: string) => void,
  onStatus: (msg: SseStatusMsg) => void
): () => void {
  const es = new EventSource(`${BASE}/api/jobs/${jobId}/stream`);

  es.onmessage = (e: MessageEvent) => {
    try {
      const msg = JSON.parse(e.data) as SseMsg;
      if (msg.type === "log") {
        onLog(msg.text);
      } else if (msg.type === "status") {
        onStatus(msg);
        es.close();
      }
    } catch {
      // ignore parse errors
    }
  };

  es.onerror = () => {
    es.close();
  };

  return () => es.close();
}

// ── Outputs ───────────────────────────────────────────────────────────────

export interface OutputFile {
  name: string;
  path: string;
  size_bytes: number;
  created_at: number;
}

export async function fetchOutputs(): Promise<OutputFile[]> {
  const r = await fetch(`${BASE}/api/outputs`);
  if (!r.ok) throw new Error(`GET /api/outputs: ${r.status}`);
  return r.json();
}
