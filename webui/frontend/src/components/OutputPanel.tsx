import { createResource, For, Show } from "solid-js";
import { fetchOutputs } from "../api";
import type { OutputFile } from "../api";

function formatBytes(b: number): string {
  if (b > 1e6) return `${(b / 1e6).toFixed(1)} MB`;
  if (b > 1e3) return `${(b / 1e3).toFixed(0)} KB`;
  return `${b} B`;
}

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

export default function OutputPanel() {
  const [files, { refetch }] = createResource<OutputFile[]>(fetchOutputs);

  return (
    <div style="max-width:800px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
        <h2 style="font-size:16px; font-weight:700;">Generated Videos</h2>
        <button
          onClick={() => refetch()}
          style="font-size:12px; color:var(--muted); background:var(--surface); border:1px solid var(--border); border-radius:5px; padding:4px 12px; cursor:pointer;"
        >
          Refresh
        </button>
      </div>

      <Show when={files.loading}>
        <p style="color:var(--muted);">Loading…</p>
      </Show>

      <Show when={files.error}>
        <p style="color:var(--error);">Error loading outputs: {String(files.error)}</p>
      </Show>

      <Show when={files() && files()!.length === 0}>
        <p style="color:var(--muted);">No videos generated yet. Run the pipeline from the Dashboard.</p>
      </Show>

      <For each={files()}>
        {(file) => (
          <div
            class="card"
            style="margin-bottom:10px; display:flex; align-items:center; gap:16px;"
          >
            {/* Video thumbnail placeholder */}
            <div
              style="
                width:80px; height:48px; background:#0a0c12;
                border:1px solid var(--border); border-radius:5px;
                display:flex; align-items:center; justify-content:center;
                font-size:20px; flex-shrink:0;
              "
            >
              🎬
            </div>

            <div style="flex:1; overflow:hidden;">
              <div style="font-weight:600; font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                {file.name}
              </div>
              <div style="font-size:11px; color:var(--muted); margin-top:2px;">
                {formatBytes(file.size_bytes)} · {formatDate(file.created_at)}
              </div>
              <div style="font-size:10px; color:var(--muted); margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                {file.path}
              </div>
            </div>

            <a
              href={`/api/outputs/download?path=${encodeURIComponent(file.path)}`}
              download={file.name}
              style="
                font-size:12px; color:var(--accent); text-decoration:none;
                border:1px solid var(--accent); border-radius:5px; padding:4px 12px;
                white-space:nowrap;
              "
            >
              Download
            </a>
          </div>
        )}
      </For>
    </div>
  );
}
