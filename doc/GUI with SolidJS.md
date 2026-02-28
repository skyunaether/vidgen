Claude’s Plan
Plan: Replace TUI with SolidJS + Litestar Web Application
Context
The existing vidgen app uses Textual (Python TUI) for its UI. The TUI runs the pipeline in a worker thread, streams log output back to the UI via call_from_thread(), and exposes 3 input modes (auto/manual/files). The goal is to replace this with a modern, high-performance web application while keeping the Python engine code (vidgen/) intact with minimal changes. The new UI must also expose controls for the multi-agent orchestration system (ProjectManager → QC → DevTeam iterative loop).

Tech Stack Decision
Frontend: SolidJS + TypeScript + Vite
Justification (benchmark-backed):

js-framework-benchmark ranks SolidJS #1–2 among all frameworks (consistently outperforms Svelte, Vue, React).
Fine-grained reactivity with no Virtual DOM: Signals compile to direct DOM mutations. A log panel receiving 100 SSE messages/second updates only the new <div> appended — zero diffing overhead. React would re-render the entire list; SolidJS updates exactly one node.
~7 KB gzipped runtime (vs React ~45 KB, Vue ~22 KB). For a local tool opened frequently, startup latency matters.
Vite provides sub-second HMR and optimal tree-shaking for production builds.
SSE streams map perfectly to SolidJS createSignal — each event triggers a fine-grained DOM patch.
Backend: Litestar 2.x + uvicorn
Justification:

Litestar outperforms FastAPI by ~20–35% throughput in TechEmpower benchmarks due to msgspec-based serialization.
First-class SSE support: ServerSentEvent + EventStream are built-in types. No third-party sse-starlette needed.
ASGI-native: The blocking Pipeline runs in asyncio.to_thread, bridging sync engine → async SSE without an additional thread executor library.
Pydantic v2 (already in the project's requirements) is natively supported for request validation.
Python is mandatory since the entire vidgen/ engine is Python — a Rust/Go rewrite would mean rewriting 4,000+ lines of AI pipeline logic.
Transport: SSE for logs + REST for control
SSE (Server-Sent Events) over HTTP/2 for one-directional log streaming: simpler than WebSockets, auto-reconnects on drop, no heartbeat protocol needed.
REST (POST /api/jobs, POST /api/jobs/{id}/cancel, GET /api/config) for control plane.
File Structure

vidgen/                              ← repo root
├── vidgen/                          ← existing Python package (minimal changes)
│   ├── pipeline.py                  ← MODIFY: add PipelineOptions dataclass
│   ├── config.py                    ← unchanged
│   ├── tui.py                       ← kept (not deleted, for CLI fallback)
│   └── ... (all other modules)      ← unchanged
├── orchestrator.py                  ← unchanged
├── schemas/                         ← unchanged
│
└── webui/                           ← NEW: web application root
    ├── backend/                     ← Litestar server
    │   ├── __init__.py
    │   ├── app.py                   ← Litestar app + route registration + CORS + static files
    │   ├── models.py                ← Pydantic request/response models
    │   ├── job_manager.py           ← Job lifecycle: submit, cancel, status, SSE queue
    │   └── routes/
    │       ├── __init__.py
    │       ├── config.py            ← GET/POST /api/config
    │       ├── jobs.py              ← POST /api/jobs, GET /api/jobs/{id}, DELETE cancel
    │       ├── stream.py            ← GET /api/jobs/{id}/stream (SSE)
    │       └── outputs.py           ← GET /api/outputs (list generated videos)
    │
    ├── frontend/                    ← SolidJS application
    │   ├── package.json
    │   ├── vite.config.ts           ← proxy /api → :8000 in dev
    │   ├── tsconfig.json
    │   ├── index.html
    │   └── src/
    │       ├── App.tsx              ← Root with tab routing (Dashboard / Config / Outputs)
    │       ├── store.ts             ← Global signals (config, jobState, logs, options)
    │       ├── api.ts               ← fetch wrappers + SSE EventSource client
    │       └── components/
    │           ├── InputPanel.tsx       ← Mode selector + prompt/story/files input
    │           ├── PipelineToggles.tsx  ← Checkboxes per pipeline stage
    │           ├── MultiAgentPanel.tsx  ← Enable toggle + max_iterations + iteration status
    │           ├── ConfigPanel.tsx      ← API keys, output dir, audio models
    │           ├── LogPanel.tsx         ← SSE-driven terminal log output
    │           ├── StatusBar.tsx        ← Job state indicator
    │           └── OutputPanel.tsx      ← Video file list with download links
    │
    ├── start.py                     ← Launcher: starts uvicorn + opens browser
    └── requirements-webui.txt       ← litestar[full], uvicorn[standard], msgspec
API Contract
Data Models (webui/backend/models.py)

class PipelineOptions(BaseModel):
    story_review: bool = True      # Stage 1.5 (Llama review loop)
    image_gen: bool = True         # Stage 2
    video_gen: bool = True         # Stage 3
    narration: bool = True         # Stage 4
    music_gen: bool = True         # Stage 4.5
    compile: bool = True           # Stage 5

class MultiAgentOptions(BaseModel):
    enabled: bool = False
    max_iterations: int = 3

class ExecuteRequest(BaseModel):
    mode: Literal["auto", "manual", "files"]
    prompt: str = ""               # auto mode
    story: str = ""                # manual mode (pipe-separated)
    files_path: str = ""           # files mode
    use_test_mode: bool = False    # placeholder images (no API calls)
    pipeline: PipelineOptions = PipelineOptions()
    multi_agent: MultiAgentOptions = MultiAgentOptions()
    # Config overrides (applied on top of ~/.vidgen/config.json):
    use_ai_music: bool | None = None
    use_ai_tts: bool | None = None

class JobStatus(BaseModel):
    job_id: str
    state: Literal["queued", "running", "done", "cancelled", "failed"]
    started_at: str | None
    finished_at: str | None
    output_path: str | None        # final MP4 path when done
    error: str | None

class ConfigPayload(BaseModel):
    hf_token: str = ""
    gemini_api_key: str = ""
    output_dir: str = "output"
    use_ai_music: bool = True
    use_ai_tts: bool = False
    music_model: str = "facebook/musicgen-small"
    tts_model: str = "parler-tts/parler-tts-mini-v1"
REST Endpoints
Method	Path	Description
GET	/api/config	Return current config (keys masked)
POST	/api/config	Save updated config to ~/.vidgen/config.json
POST	/api/jobs	Submit execute request → returns {job_id} immediately
GET	/api/jobs/{job_id}	Poll job status
POST	/api/jobs/{job_id}/cancel	Cancel running job
GET	/api/jobs/{job_id}/stream	SSE stream of log lines for this job
GET	/api/outputs	List all MP4 files in output dir with metadata
SSE Message Format

data: {"type": "log", "text": "Stage 2/5: Image generation...", "ts": 1709012345.2}\n\n
data: {"type": "status", "state": "done", "output": "output/vidgen_20260227.mp4"}\n\n
data: {"type": "agent", "agent": "QualityControl", "state": "running"}\n\n
Step 1: Minimal Pipeline Modification (vidgen/pipeline.py)
Add PipelineOptions to skip stages without restructuring existing code:


# Add to top of pipeline.py
from dataclasses import dataclass as _dc, field as _field

@_dc
class PipelineOptions:
    story_review: bool = True
    image_gen: bool = True
    video_gen: bool = True
    narration: bool = True
    music_gen: bool = True
    compile: bool = True

# Modify Pipeline.__init__ to accept options:
def __init__(self, config, progress_cb=None, use_placeholders=False, options=None):
    ...
    self.options = options or PipelineOptions()

# Modify Pipeline.run() to gate each stage:
def run(self, prompt: str) -> Path:
    ...
    if self.options.story_review:
        self.step_review_story(prompt)
    if self.options.image_gen:
        media_paths = self.step_generate_images()
    if self.options.video_gen:
        self.step_generate_videos(media_paths)
    if self.options.narration:
        narration_path = self.step_generate_narration()
    if self.options.music_gen:
        music_path = self.step_generate_music(prompt)
    if self.options.compile:
        return self.step_compile(media_paths, music_path, narration_path)
Step 2: Job Manager (webui/backend/job_manager.py)

import asyncio, threading, uuid, time
from pathlib import Path
from vidgen.pipeline import Pipeline, PipelineOptions
from vidgen.config import Config

class JobManager:
    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._queues: dict[str, asyncio.Queue] = {}

    def submit(self, request: ExecuteRequest) -> str:
        job_id = str(uuid.uuid4())[:8]
        queue = asyncio.Queue()
        self._queues[job_id] = queue
        self._jobs[job_id] = {"state": "queued", "started_at": None,
                               "finished_at": None, "output": None, "error": None}

        # progress_cb puts log lines into queue (thread-safe)
        loop = asyncio.get_event_loop()
        def progress_cb(msg: str):
            loop.call_soon_threadsafe(queue.put_nowait,
                                      {"type": "log", "text": msg, "ts": time.time()})

        # Run pipeline in thread pool (non-blocking)
        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, request, progress_cb, loop),
            daemon=True
        )
        thread.start()
        return job_id

    def _run_job(self, job_id, request, progress_cb, loop):
        self._jobs[job_id]["state"] = "running"
        self._jobs[job_id]["started_at"] = time.time()
        try:
            config = Config.load()
            # Apply overrides from request
            if request.use_ai_music is not None:
                config.use_ai_music = request.use_ai_music
            if request.use_ai_tts is not None:
                config.use_ai_tts = request.use_ai_tts

            options = PipelineOptions(**request.pipeline.model_dump())

            if request.multi_agent.enabled:
                output = self._run_orchestrator(request, progress_cb)
            else:
                pipeline = Pipeline(config, progress_cb=progress_cb,
                                    use_placeholders=request.use_test_mode,
                                    options=options)
                self._jobs[job_id]["_pipeline"] = pipeline
                output = pipeline.run(request.prompt or request.story)

            self._jobs[job_id].update(state="done", output=str(output),
                                      finished_at=time.time())
            loop.call_soon_threadsafe(
                self._queues[job_id].put_nowait,
                {"type": "status", "state": "done", "output": str(output)}
            )
        except Exception as e:
            self._jobs[job_id].update(state="failed", error=str(e),
                                      finished_at=time.time())
            loop.call_soon_threadsafe(
                self._queues[job_id].put_nowait,
                {"type": "status", "state": "failed", "error": str(e)}
            )

    def cancel(self, job_id: str):
        job = self._jobs.get(job_id)
        pipeline = job.get("_pipeline") if job else None
        if pipeline:
            pipeline.cancel()
        if job:
            job["state"] = "cancelled"

    async def stream(self, job_id: str):
        """Async generator of SSE dicts for a job."""
        queue = self._queues.get(job_id)
        if not queue:
            return
        while True:
            msg = await queue.get()
            yield msg
            if msg.get("type") == "status":
                break

job_manager = JobManager()
Step 3: Litestar App (webui/backend/app.py)

from litestar import Litestar, get, post
from litestar.response import ServerSentEvent, Response
from litestar.static_files import StaticFilesConfig
from litestar.config.cors import CORSConfig

@post("/api/jobs")
async def create_job(data: ExecuteRequest) -> dict:
    job_id = job_manager.submit(data)
    return {"job_id": job_id}

@get("/api/jobs/{job_id:str}/stream")
async def stream_job(job_id: str) -> ServerSentEvent:
    async def event_generator():
        async for msg in job_manager.stream(job_id):
            yield {"data": json.dumps(msg)}
    return ServerSentEvent(event_generator())

@get("/api/jobs/{job_id:str}")
async def get_job(job_id: str) -> JobStatus: ...

@post("/api/jobs/{job_id:str}/cancel")
async def cancel_job(job_id: str) -> dict: ...

@get("/api/config")
async def get_config() -> ConfigPayload: ...

@post("/api/config")
async def save_config(data: ConfigPayload) -> dict: ...

@get("/api/outputs")
async def list_outputs() -> list[dict]: ...

app = Litestar(
    route_handlers=[create_job, stream_job, get_job, cancel_job,
                    get_config, save_config, list_outputs],
    cors_config=CORSConfig(allow_origins=["http://localhost:5173"]),
    static_files_config=[StaticFilesConfig(path="/", directories=["frontend/dist"],
                                           html_mode=True)],
)
Step 4: SolidJS Frontend
Global Store (src/store.ts)

import { createSignal, createStore } from "solid-js/store";

// Reactive app state using SolidJS signals (no VDOM diffing)
export const [config, setConfig] = createStore({
  hf_token: "", gemini_api_key: "", output_dir: "output",
  use_ai_music: true, use_ai_tts: false,
  music_model: "facebook/musicgen-small",
  tts_model: "parler-tts/parler-tts-mini-v1",
});

export const [pipelineOpts, setPipelineOpts] = createStore({
  story_review: true, image_gen: true, video_gen: true,
  narration: true, music_gen: true, compile: true,
});

export const [multiAgentOpts, setMultiAgentOpts] = createStore({
  enabled: false, max_iterations: 3,
});

export const [jobState, setJobState] = createSignal<
  "idle" | "queued" | "running" | "done" | "failed" | "cancelled"
>("idle");

export const [logs, setLogs] = createSignal<string[]>([]);
export const [activeTab, setActiveTab] = createSignal<"dashboard"|"config"|"outputs">("dashboard");
SSE Log Consumer (src/api.ts)

export function streamJob(jobId: string, onLog: (text: string) => void,
                          onDone: (output: string) => void) {
  const es = new EventSource(`/api/jobs/${jobId}/stream`);
  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "log") onLog(msg.text);
    if (msg.type === "status") {
      onDone(msg.output ?? "");
      es.close();
    }
  };
  return () => es.close(); // cleanup
}
Key UI Components
LogPanel.tsx — Terminal-like, SSE-driven:


// Fine-grained: only the new <p> is added to DOM on each log entry
const LogPanel = () => (
  <div class="log-panel font-mono text-sm bg-black text-green-400 overflow-y-auto h-80 p-2">
    <For each={logs()}>
      {(line) => <p>{line}</p>}
    </For>
  </div>
);
MultiAgentPanel.tsx:


const MultiAgentPanel = () => (
  <div class="card">
    <h3>Multi-Agent Orchestration</h3>
    <label><input type="checkbox" checked={multiAgentOpts.enabled}
      onChange={e => setMultiAgentOpts("enabled", e.target.checked)} />
      Enable (ProjectManager → QC → DevTeam loop)</label>
    <Show when={multiAgentOpts.enabled}>
      <label>Max Iterations:
        <input type="number" min={1} max={10} value={multiAgentOpts.max_iterations}
          onInput={e => setMultiAgentOpts("max_iterations", +e.target.value)} />
      </label>
    </Show>
  </div>
);
PipelineToggles.tsx:


const STAGES = [
  ["story_review", "Stage 1.5: Story Review (AI)"],
  ["image_gen",    "Stage 2: Image Generation"],
  ["video_gen",    "Stage 3: Video Animation"],
  ["narration",    "Stage 4: Narration (TTS)"],
  ["music_gen",    "Stage 4.5: Music Generation"],
  ["compile",      "Stage 5: Compile Video"],
] as const;

const PipelineToggles = () => (
  <div class="card">
    <h3>Pipeline Stages</h3>
    <For each={STAGES}>
      {([key, label]) => (
        <label>
          <input type="checkbox" checked={pipelineOpts[key]}
            onChange={e => setPipelineOpts(key, e.target.checked)} />
          {label}
        </label>
      )}
    </For>
  </div>
);
Execute Button flow (App.tsx):


const handleExecute = async () => {
  setJobState("queued");
  setLogs([]);
  const { job_id } = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode: inputMode(), prompt: prompt(), story: story(), files_path: filesPath(),
      use_test_mode: testMode(),
      pipeline: pipelineOpts,
      multi_agent: multiAgentOpts,
      use_ai_music: config.use_ai_music,
      use_ai_tts: config.use_ai_tts,
    }),
  }).then(r => r.json());

  setActiveJobId(job_id);
  setJobState("running");
  streamJob(job_id,
    (text) => setLogs(prev => [...prev, text]),   // append only — SolidJS: O(1) DOM patch
    (output) => { setJobState("done"); setOutputPath(output); }
  );
};
Step 5: Dev Launcher (webui/start.py)

"""Launch backend (uvicorn) + open browser.
For development: run frontend separately with `npm run dev` in webui/frontend/."""
import subprocess, time, webbrowser, sys, os

def main():
    print("Starting VidGen Web UI backend on http://localhost:8000 ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "webui.backend.app:app",
         "--reload", "--port", "8000"],
        cwd=os.path.dirname(__file__) + "/.."
    )
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")
    backend.wait()
Vite Proxy for Dev (frontend/vite.config.ts)

export default defineConfig({
  plugins: [solidPlugin()],
  server: {
    proxy: { "/api": "http://localhost:8000" }
  }
});
Orchestrator Integration in JobManager
When multi_agent.enabled=True, JobManager._run_job runs the orchestrator as an async subprocess:


async def _run_orchestrator(self, request, progress_cb):
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "orchestrator.py",
        "--prompt", request.prompt,
        "--max-iterations", str(request.multi_agent.max_iterations),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    async for line in proc.stdout:
        progress_cb(line.decode().rstrip())
    await proc.wait()
Files to Create (New)
File	Action
webui/backend/__init__.py	create
webui/backend/app.py	create
webui/backend/models.py	create
webui/backend/job_manager.py	create
webui/backend/routes/config.py	create
webui/backend/routes/jobs.py	create
webui/backend/routes/stream.py	create
webui/backend/routes/outputs.py	create
webui/frontend/package.json	create
webui/frontend/vite.config.ts	create
webui/frontend/tsconfig.json	create
webui/frontend/index.html	create
webui/frontend/src/App.tsx	create
webui/frontend/src/store.ts	create
webui/frontend/src/api.ts	create
webui/frontend/src/components/*.tsx (6 components)	create
webui/start.py	create
webui/requirements-webui.txt	create
Files to Modify (Existing)
File	Change
vidgen/pipeline.py	Add PipelineOptions dataclass (5 bool fields); gate each step_* call in run()
Verification
Install backend deps: pip install -r webui/requirements-webui.txt
Install frontend deps: cd webui/frontend && npm install
Start backend: python -m uvicorn webui.backend.app:app --reload --port 8000
Start frontend dev server: cd webui/frontend && npm run dev (Vite proxies /api → :8000)
Open http://localhost:5173
Test: Enter a prompt, disable "Video Animation" toggle, click Execute
Verify: SSE log lines stream into LogPanel in real-time; video file appears in Outputs tab
Test multi-agent: Enable multi-agent toggle, verify orchestrator subprocess logs appear
Production build: npm run build → uvicorn webui.backend.app:app --port 8000 (serves frontend/dist/)


Update Todos

Modify vidgen/pipeline.py: add PipelineOptions dataclass + stage gating

Create webui/backend: models.py, job_manager.py, app.py, routes/

Create webui/frontend: package.json, vite.config.ts, tsconfig.json, index.html

Create frontend store.ts, api.ts, App.tsx

Create frontend components: InputPanel, PipelineToggles, MultiAgentPanel, ConfigPanel, LogPanel, StatusBar, OutputPanel

Create webui/start.py and webui/requirements-webui.txt

Install backend deps and verify server starts

Install frontend deps and verify dev server starts
Update Todos

Modify vidgen/pipeline.py: add PipelineOptions dataclass + stage gating

Create webui/backend: models.py, job_manager.py, app.py, routes/

Create webui/frontend: package.json, vite.config.ts, tsconfig.json, index.html

Create frontend store.ts, api.ts, App.tsx

Create frontend components: InputPanel, PipelineToggles, MultiAgentPanel, ConfigPanel, LogPanel, StatusBar, OutputPanel

Create webui/start.py and webui/requirements-webui.txt

Install backend deps and verify server starts

Install frontend deps and verify dev server starts
