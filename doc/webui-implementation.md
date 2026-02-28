# VidGen Web UI — Implementation Document

> **Date:** 2026-02-27
> **Branch:** `devteam/20260227_220419/fix-duration-and-style`
> **Scope:** Replace the Textual TUI with a SolidJS + Litestar web application

---

## 1. Background & Objective

The existing `vidgen` app used a **Textual** (Python TUI) as its only interactive interface. It ran the pipeline in a worker thread, streamed progress back via `call_from_thread()`, and exposed three input modes (auto / manual / files).

**Goals:**
- Replace the TUI with a browser-based web UI — no terminal required
- Keep the Python engine (`vidgen/`) fully intact with minimal changes
- Expose granular control over each pipeline stage (enable/disable individual steps)
- Integrate the multi-agent orchestration loop (ProjectManager → QC → DevTeam) as an optional UI-controlled feature
- Stream log output to the browser in real-time with sub-millisecond DOM update latency

---

## 2. Tech Stack Decision

### Frontend: SolidJS + TypeScript + Vite

| Criterion | SolidJS | React | Svelte |
|-----------|---------|-------|--------|
| Runtime bundle | ~7 KB gzip | ~45 KB | ~10 KB |
| DOM update model | Fine-grained signals (no VDOM) | Virtual DOM diff | Compiled reactive |
| js-framework-benchmark rank | #1–2 | #20+ | #5–8 |
| SSE streaming fit | Perfect — one signal per message | Re-renders full list | Good |

**Why SolidJS wins for this use case:** the log panel receives hundreds of SSE messages per second. SolidJS `<For>` with signals appends exactly one `<p>` node per message — O(1) DOM work. React would diff the entire list on every message.

**Vite** provides sub-second HMR and tree-shakes the 35 KB uncompressed (12.65 KB gzip) production bundle.

### Backend: Litestar 2.x + uvicorn

| Criterion | Litestar | FastAPI |
|-----------|----------|---------|
| TechEmpower throughput | ~20–35% faster | Baseline |
| SSE support | Built-in `ServerSentEvent` type | Third-party `sse-starlette` |
| Serialization | `msgspec` (fastest Python serializer) | Pydantic (slower) |
| OpenAPI docs | Auto-generated at `/schema` | Auto-generated |

Python is mandatory — rewriting the 4,000+ line engine in another language was out of scope.

### Transport: SSE + REST

- **SSE** (`GET /api/jobs/{id}/stream`) for one-directional log streaming: auto-reconnects, no heartbeat, HTTP/2 compatible
- **REST** for all control operations (submit, cancel, poll, config)

---

## 3. Architecture

### File Layout

```
vidgen/                              (repo root)
├── vidgen/                          (existing engine — minimal changes)
│   ├── pipeline.py                  MODIFIED: PipelineOptions dataclass added
│   └── ... (all other modules)      unchanged
├── orchestrator.py                  unchanged
├── run_gui.ps1                      NEW: Windows PowerShell launcher
│
└── webui/                           NEW: web application
    ├── requirements-webui.txt
    ├── start.py                     cross-platform Python launcher
    ├── backend/
    │   ├── app.py                   Litestar app + CORS + static file serving
    │   ├── models.py                Pydantic request/response schemas
    │   ├── job_manager.py           job lifecycle + asyncio.Queue SSE bridge
    │   └── routes/
    │       ├── config.py            GET/POST /api/config
    │       ├── jobs.py              POST /api/jobs, GET status, POST cancel
    │       ├── stream.py            GET /api/jobs/{id}/stream  (SSE)
    │       └── outputs.py           GET /api/outputs, GET /api/outputs/download
    └── frontend/
        ├── package.json
        ├── vite.config.ts           /api proxy → :8000 in dev
        ├── tsconfig.json
        ├── index.html
        └── src/
            ├── index.tsx
            ├── App.tsx              3-tab layout: Dashboard / Settings / Outputs
            ├── store.ts             global SolidJS signals
            ├── api.ts               typed REST + SSE client
            └── components/
                ├── InputPanel.tsx       mode selector + prompt/story/files
                ├── PipelineToggles.tsx  per-stage checkboxes
                ├── MultiAgentPanel.tsx  agent loop toggle + iteration count
                ├── ConfigPanel.tsx      API keys, output dir, audio models
                ├── LogPanel.tsx         SSE terminal log (auto-scroll)
                ├── StatusBar.tsx        job state indicator + output path
                └── OutputPanel.tsx      video list with download
```

### Data Flow

```
Browser                         Litestar (port 8000)              Engine threads
   │                                    │                                │
   │── POST /api/jobs ────────────────► │                                │
   │◄─ {job_id} ──────────────────────  │── threading.Thread ──────────► │
   │                                    │                                │
   │── GET /api/jobs/{id}/stream ──────► │                                │
   │                                    │   asyncio.Queue (SSE bridge)   │
   │◄─ data: {"type":"log", ...} ──────  │◄── loop.call_soon_threadsafe ─ │
   │◄─ data: {"type":"log", ...} ──────  │                                │
   │◄─ data: {"type":"status",...} ────  │◄── job done / error ─────────  │
   │   (EventSource closes)             │                                │
```

---

## 4. API Contract

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/config` | Read config (API keys masked to `hf_S…avdw` format) |
| `POST` | `/api/config` | Save config to `~/.vidgen/config.json` |
| `POST` | `/api/jobs` | Submit job → `{"job_id": "ab23cfc3"}` |
| `GET` | `/api/jobs/{id}` | Poll `JobStatus` |
| `POST` | `/api/jobs/{id}/cancel` | Cancel (calls `pipeline.cancel()`) |
| `GET` | `/api/jobs/{id}/stream` | **SSE** — streams log + final status |
| `GET` | `/api/outputs` | List MP4 files in output dir |
| `GET` | `/api/outputs/download?path=...` | Stream MP4 file for download |
| `GET` | `/schema` | Auto-generated OpenAPI docs (Litestar) |

### Execute Request Payload

```json
{
  "mode": "auto",
  "prompt": "A cinematic story about space",
  "story": "",
  "files_path": "",
  "use_test_mode": false,
  "pipeline": {
    "story_review": true,
    "image_gen": true,
    "video_gen": true,
    "narration": true,
    "music_gen": true,
    "compile": true
  },
  "multi_agent": {
    "enabled": false,
    "max_iterations": 3
  },
  "use_ai_music": null,
  "use_ai_tts": null
}
```

### SSE Message Format

```
data: {"type": "log",    "text": "Stage 2/5: Image generation...", "ts": 1772200390.8}\n\n
data: {"type": "status", "state": "done", "output": "output/vidgen_20260227.mp4"}\n\n
data: {"type": "status", "state": "failed", "error": "GEMINI_API_KEY not set"}\n\n
```

---

## 5. Pipeline Changes (`vidgen/pipeline.py`)

Added `PipelineOptions` dataclass and wired it into `Pipeline.__init__` and `Pipeline.run()`:

```python
@dataclass
class PipelineOptions:
    story_review: bool = True   # Stage 1.5: AI reviewer-refiner loop
    image_gen: bool = True      # Stage 2: image generation
    video_gen: bool = True      # Stage 3: video animation
    narration: bool = True      # Stage 4: TTS narration
    music_gen: bool = True      # Stage 4.5: background music
    compile: bool = True        # Stage 5: final compilation
```

Each stage in `run()` is now gated:

```python
if self.options.story_review:
    self.step_review_story(prompt)
if self.options.image_gen:
    media_paths = self.step_generate_images()
# ... etc.
if not self.options.compile:
    self.progress_cb("Stage 5/5: Compilation skipped.")
    return None   # job state → "done" with output_path = null
```

`run()` return type changed from `Path` to `Path | None` to handle compile-disabled case cleanly.

---

## 6. Todo List (Completed)

| # | Task | Status |
|---|------|--------|
| 1 | Modify `vidgen/pipeline.py`: add `PipelineOptions` + stage gating | ✅ Done |
| 2 | Create `webui/backend/`: `models.py`, `job_manager.py`, `app.py`, `routes/` | ✅ Done |
| 3 | Create `webui/frontend/`: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html` | ✅ Done |
| 4 | Create `frontend/src/`: `store.ts`, `api.ts`, `App.tsx` | ✅ Done |
| 5 | Create 7 frontend components | ✅ Done |
| 6 | Create `webui/start.py` and `webui/requirements-webui.txt` | ✅ Done |
| 7 | Install backend deps, verify server starts, smoke-test all API routes | ✅ Done |
| 8 | Install frontend deps, verify `npm run build` produces valid dist | ✅ Done |
| 9 | Create `run_gui.ps1` (Windows launcher with port conflict resolution) | ✅ Done |

---

## 7. Known Bugs Fixed (Gemini / Veo)

During this session, five bugs in `vidgen/utils/gemini_client.py` were also fixed:

| # | Bug | Fix |
|---|-----|-----|
| 1 | `from .config import Config` — wrong relative import | `from ..config import Config` |
| 2 | `client.operations.get(name=operation.name)` — invalid kwarg, raises `TypeError` | `client.operations.get(operation)` (positional) |
| 3 | `while operation.response is None` — fragile polling condition | `while not operation.done` |
| 4 | Convoluted response parsing with regex fallback | Direct: `operation.response.generated_videos[0].video.uri` |
| 5 | Download returns 403 without auth | Added `x-goog-api-key` header to `requests.get()` |

---

## 8. How to Run

### Prerequisites

```bash
# One-time setup
pip install -r webui/requirements-webui.txt
cd webui/frontend && npm install && npm run build && cd ../..
```

### Windows (PowerShell)

```powershell
# Production — backend serves built frontend on :8000
.\run_gui.ps1

# Development — Vite HMR on :5173, backend --reload on :8000
.\run_gui.ps1 -Dev
```

`run_gui.ps1` automatically kills any existing process on ports 8000 / 5173 before starting.

### Cross-platform (Python)

```bash
python webui/start.py          # production
python webui/start.py --dev    # dev mode
```

### Manual

```bash
# Terminal 1 — backend
python -m uvicorn webui.backend.app:app --reload --port 8000

# Terminal 2 — frontend (dev)
cd webui/frontend && npm run dev

# Open http://localhost:5173
```

---

## 9. Verification Checklist

- [x] `GET /api/config` returns masked keys and correct defaults
- [x] `GET /api/outputs` lists existing MP4 files with size + timestamp
- [x] `POST /api/jobs` returns `job_id` within 50 ms
- [x] `GET /api/jobs/{id}` transitions: `queued → running → done`
- [x] `GET /api/jobs/{id}/stream` streams log lines via SSE, closes on status message
- [x] Pipeline with `compile: false` finishes with `state: "done"`, `output_path: null` (not "failed")
- [x] Production `npm run build` succeeds: 35.1 KB JS, 12.65 KB gzip
- [x] Backend serves `frontend/dist/index.html` at `GET /` (production mode)
- [x] OpenAPI docs available at `GET /schema`
