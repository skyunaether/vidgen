"""Textual TUI application for vidgen."""
from __future__ import annotations

import re
import threading
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    TextArea,
)

from .config import Config
from .pipeline import Pipeline, PipelineCancelled
from .scriptgen import parse_markdown_story, parse_user_story

# Regex to detect stage-header lines like "📝 Stage 1/5: ..."
_STAGE_RE = re.compile(r"Stage\s+(\d+(?:\.\d+)?)/5[:\s]+(.*)", re.IGNORECASE)

# Input mode constants
_MODE_AUTO   = "auto"
_MODE_MANUAL = "manual"
_MODE_FILES  = "files"

# Pre-filled example for the manual TextArea
_STORY_PLACEHOLDER = """\
# One scene per line:  narration | visual description | seconds | image/video
# The last two fields are optional (defaults: 10s, image).
# Lines starting with # are ignored.

Some dreams are too powerful to stay on the ground. | A lone man on a cliff at dawn, cinematic golden hour | 8
For years, he watched the birds. | Close-up of man's eyes reflecting birds, bokeh sky | 10
He built the wings with care. | Craftsman assembling giant wings in a workshop | 12 | video
He leapt — and for one breathless moment, he was flying. | Man with wings soaring above green hills, epic cinematic | 12 | video
If you dare to dream it — you can fly. | Man silhouetted against blazing sunset, inspirational | 8
"""


def _rich_format(msg: str) -> str:
    """Apply Rich markup to key pipeline messages for better readability."""
    if _STAGE_RE.search(msg):
        return f"[bold cyan]{msg}[/bold cyan]"
    if any(x in msg for x in ("✅", "🎉", "approved", "Done!")):
        return f"[bold green]{msg}[/bold green]"
    if any(x in msg for x in ("⚠", "⛔", "✗", "failed", "skipping")):
        return f"[yellow]{msg}[/yellow]"
    if msg.strip().startswith("✓"):
        return f"[green]{msg}[/green]"
    if msg.strip().startswith("Score:"):
        return f"[bold magenta]{msg}[/bold magenta]"
    if any(x in msg for x in ("🔍", "✍", "Reviewer", "Refiner", "Iteration")):
        return f"[dim cyan]{msg}[/dim cyan]"
    if msg.strip().startswith("📖 Using") or msg.strip().startswith("📄"):
        return f"[bold blue]{msg}[/bold blue]"
    return msg


class VidGenApp(App):
    """Video Generation Pipeline TUI."""

    TITLE = "VidGen — Automated Video Generator"
    CSS = """
    Screen {
        layout: vertical;
    }

    #input-panel {
        dock: top;
        height: auto;
        padding: 1 2 0 2;
        background: $surface;
    }

    #mode-row {
        height: auto;
        padding: 0 0 1 0;
        align: left middle;
    }

    #mode-label {
        width: auto;
        padding: 0 1 0 0;
    }

    #mode-select {
        width: 46;
    }

    /* Auto-prompt section */
    #auto-section {
        height: auto;
        padding: 0 0 1 0;
    }

    #auto-hint {
        height: auto;
        color: $text-muted;
    }

    #prompt-input {
        width: 1fr;
        margin-top: 1;
    }

    /* Manual story section */
    #manual-section {
        height: auto;
        padding: 0 0 1 0;
    }

    #manual-hint {
        height: auto;
        color: $text-muted;
        padding: 0 0 1 0;
    }

    #story-input {
        height: 14;
        width: 1fr;
    }

    /* Markdown files section */
    #files-section {
        height: auto;
        padding: 0 0 1 0;
    }

    #files-hint {
        height: auto;
        color: $text-muted;
        padding: 0 0 1 0;
    }

    #files-path-input {
        width: 1fr;
        margin-top: 1;
    }

    /* Button bar */
    #button-bar {
        height: 3;
        padding: 0 2;
        align: left middle;
        background: $surface;
    }

    #button-bar Button {
        margin-right: 1;
    }

    /* Log */
    #log-area {
        height: 1fr;
        padding: 0 2 1 2;
    }

    /* Status bar */
    #status-bar {
        dock: bottom;
        height: 3;
        padding: 1 2;
        background: $accent;
        color: $text;
    }

    .placeholder-warning {
        color: $warning;
        padding: 0 0 1 0;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("ctrl+g", "generate",  "Generate",  show=True),
        Binding("ctrl+t", "test",      "Test mode",  show=True),
        Binding("ctrl+c", "cancel",    "Cancel",     show=True),
        Binding("ctrl+l", "clear_log", "Clear log",  show=True),
        Binding("ctrl+q", "quit",      "Quit",       show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config = Config.load()
        self._pipeline: Pipeline | None = None
        self._running = False
        self._thread_id = threading.get_ident()
        self._mode = _MODE_AUTO
        self._cancel_requested = threading.Event()

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="input-panel"):
            # Mode selector row
            with Horizontal(id="mode-row"):
                yield Label("Input mode:", id="mode-label")
                yield Select(
                    [
                        ("🪄  Auto — generate story from prompt",       _MODE_AUTO),
                        ("✍️   Manual — type full story in-app",         _MODE_MANUAL),
                        ("📁  Markdown — load story from .md file(s)",  _MODE_FILES),
                    ],
                    value=_MODE_AUTO,
                    id="mode-select",
                    allow_blank=False,
                )

            # HF token warning
            if not self._config.hf_token:
                yield Static(
                    "⚠  No HF_TOKEN found — AI image/review stages will use placeholders. "
                    "Set HF_TOKEN env var or add it to ~/.vidgen/config.json",
                    classes="placeholder-warning",
                )

            # --- Auto mode section ---
            with Vertical(id="auto-section"):
                yield Label(
                    "Enter any video idea — the pipeline will write, review, illustrate, "
                    "narrate and score it automatically:",
                    id="auto-hint",
                )
                yield Input(
                    placeholder="e.g., A man who learns to fly with giant mechanical wings",
                    id="prompt-input",
                )

            # --- Manual mode section (hidden by default) ---
            with Vertical(id="manual-section"):
                yield Label(
                    "Enter your story below — one scene per line:\n"
                    "  [bold]narration | visual description[/bold]  "
                    "[ | seconds ]  [ | image / video ]\n"
                    "Lines starting with # are ignored.  "
                    "See [bold]assets/story_template.md[/bold] for the markdown format.",
                    id="manual-hint",
                    markup=True,
                )
                yield TextArea(
                    _STORY_PLACEHOLDER,
                    id="story-input",
                    tab_behavior="indent",
                )

            # --- Markdown files section (hidden by default) ---
            with Vertical(id="files-section"):
                yield Label(
                    "Enter a path to a [bold].md[/bold] story file or a directory of "
                    "[bold].md[/bold] files.\n"
                    "  • Single file  → 1 video\n"
                    "  • Directory   → 1 video per [bold].md[/bold] file (processed sequentially)\n"
                    "  • Comma-separated paths → multiple files\n\n"
                    "See [bold]assets/story_template.md[/bold] for the expected format.",
                    id="files-hint",
                    markup=True,
                )
                yield Input(
                    placeholder="e.g., ~/stories/flying_man.md  or  ~/stories/",
                    id="files-path-input",
                )

        with Horizontal(id="button-bar"):
            yield Button("🚀 Generate",              id="btn-generate", variant="primary")
            yield Button("⛔ Cancel",                id="btn-cancel",   variant="error",   disabled=True)
            yield Button("🧪 Test (placeholders)",   id="btn-test",     variant="warning")
            yield Button("🗑  Clear log",             id="btn-clear",    variant="default")

        yield RichLog(id="log-area", highlight=True, markup=True, wrap=True)
        yield Static(
            "Ready. Choose a mode, enter your idea, then press 🚀 Generate.",
            id="status-bar",
        )
        yield Footer()

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Hide non-default sections after the widget tree is fully mounted."""
        self.query_one("#manual-section").display = False
        self.query_one("#files-section").display  = False

    @on(Select.Changed, "#mode-select")
    def on_mode_changed(self, event: Select.Changed) -> None:
        # Guard: ignore the initial mount-time fire if sections not ready
        value = event.value
        if value is Select.BLANK:
            return
        self._mode = str(value)
        self.query_one("#auto-section").display   = self._mode == _MODE_AUTO
        self.query_one("#manual-section").display = self._mode == _MODE_MANUAL
        self.query_one("#files-section").display  = self._mode == _MODE_FILES

    # ------------------------------------------------------------------
    # Thread-safe helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        """Progress callback: format + append to log (thread-safe)."""
        formatted = _rich_format(msg)
        if _STAGE_RE.search(msg):
            self._set_status(f"⏳ {msg.strip()}")
        if threading.get_ident() == self._thread_id:
            self._append_log(formatted)
        else:
            self.call_from_thread(self._append_log, formatted)

    def _append_log(self, msg: str) -> None:
        self.query_one("#log-area", RichLog).write(msg)

    def _set_status(self, msg: str) -> None:
        if threading.get_ident() == self._thread_id:
            self._update_status(msg)
        else:
            self.call_from_thread(self._update_status, msg)

    def _update_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    def _set_running(self, running: bool) -> None:
        self._running = running
        if threading.get_ident() == self._thread_id:
            self._update_buttons(running)
        else:
            self.call_from_thread(self._update_buttons, running)

    def _update_buttons(self, running: bool) -> None:
        self.query_one("#btn-generate", Button).disabled = running
        self.query_one("#btn-test",     Button).disabled = running
        self.query_one("#btn-cancel",   Button).disabled = not running
        self.query_one("#prompt-input", Input).disabled  = running
        self.query_one("#mode-select",  Select).disabled = running

    # ------------------------------------------------------------------
    # Button / key handlers
    # ------------------------------------------------------------------

    @on(Button.Pressed, "#btn-generate")
    def on_generate_btn(self) -> None:
        self.action_generate()

    @on(Button.Pressed, "#btn-test")
    def on_test_btn(self) -> None:
        self.action_test()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_btn(self) -> None:
        self.action_cancel()

    @on(Button.Pressed, "#btn-clear")
    def on_clear_btn(self) -> None:
        self.action_clear_log()

    def action_generate(self) -> None:
        if self._running:
            return
        self._launch(use_placeholders=False)

    def action_test(self) -> None:
        if self._running:
            return
        self._launch(use_placeholders=True)

    def action_cancel(self) -> None:
        self._cancel_requested.set()
        if self._pipeline:
            self._pipeline.cancel()
        self._append_log("[yellow]Cancelling...[/yellow]")

    def action_clear_log(self) -> None:
        self.query_one("#log-area", RichLog).clear()

    @on(Input.Submitted, "#prompt-input")
    def on_prompt_submit(self) -> None:
        if not self._running:
            self.action_generate()

    @on(Input.Submitted, "#files-path-input")
    def on_files_path_submit(self) -> None:
        if not self._running:
            self.action_generate()

    # ------------------------------------------------------------------
    # Core launch logic
    # ------------------------------------------------------------------

    def _current_mode(self) -> str:
        """Read the active mode directly from the Select widget (source of truth)."""
        try:
            val = self.query_one("#mode-select", Select).value
            if val is Select.BLANK:
                return _MODE_AUTO
            return str(val)
        except Exception:
            return self._mode  # fallback to cached value

    def _err(self, msg: str) -> None:
        """Show a validation error in both the log and the status bar."""
        self._append_log(f"[red]{msg}[/red]")
        self._update_status(f"⚠  {msg}")

    def _launch(self, use_placeholders: bool) -> None:
        """Validate inputs, then start the appropriate background thread."""
        try:
            mode = self._current_mode()

            if mode == _MODE_FILES:
                raw = self.query_one("#files-path-input", Input).value.strip()
                if not raw:
                    self._err("Please enter a file or directory path.")
                    return
                md_files = _resolve_md_paths(raw)
                if not md_files:
                    self._err(f"No .md files found at: {raw}")
                    self._append_log(
                        "[dim]Enter a path to a .md file or a directory containing .md files.[/dim]"
                    )
                    return
                self._start_files_pipeline(md_files, use_placeholders=use_placeholders)

            elif mode == _MODE_MANUAL:
                story_text = self.query_one("#story-input", TextArea).text.strip()
                if not story_text:
                    self._err("Please enter your story in the text area.")
                    return
                try:
                    scenes = parse_user_story(story_text)
                except ValueError as e:
                    self._err(f"Story parse error: {e}")
                    return
                self._start_single_pipeline(
                    prompt="", use_placeholders=use_placeholders, scenes=scenes
                )

            else:  # _MODE_AUTO
                prompt = self.query_one("#prompt-input", Input).value.strip()
                if not prompt:
                    self._err("Please enter a prompt.")
                    return
                self._start_single_pipeline(prompt, use_placeholders=use_placeholders)

        except Exception as exc:
            import traceback
            details = traceback.format_exc()
            self._err(f"Unexpected error: {exc}")
            self._append_log(f"[dim]{details}[/dim]")

    # ------------------------------------------------------------------
    # Single-file / single-prompt pipeline
    # ------------------------------------------------------------------

    def _start_single_pipeline(
        self,
        prompt: str,
        use_placeholders: bool,
        scenes=None,
    ) -> None:
        self._set_running(True)
        self._cancel_requested.clear()
        self._log("=" * 60)

        if scenes is not None:
            self._log(f"[bold]Mode:[/bold] Manual story  ({len(scenes)} scenes)")
        else:
            self._log(f"[bold]Prompt:[/bold] {prompt}")

        if use_placeholders:
            self._log("[yellow]Mode: Test — placeholder images, no AI calls[/yellow]")
        else:
            has_hf = bool(self._config.hf_token)
            self._log(
                f"[dim]HF token: {'✓ found' if has_hf else '✗ missing — will use placeholders'}[/dim]"
            )

        self._log("")
        if scenes is None:
            self._log(
                "[dim]Stages: 1 Script · 1.5 AI review · 2 Images · "
                "3 Animation · 4 Narration · 4.5 Music · 5 Compile[/dim]"
            )
        else:
            self._log(
                "[dim]Stages: 2 Images · 3 Animation · 4 Narration · 4.5 Music · 5 Compile[/dim]"
            )
            self._log("[dim](Stages 1 & 1.5 skipped — using your story)[/dim]")
        self._log("=" * 60)
        self._log("")

        self._pipeline = Pipeline(
            config=self._config,
            progress_cb=self._log,
            use_placeholders=use_placeholders,
        )
        if scenes is not None:
            self._pipeline.inject_scenes(scenes)

        thread = threading.Thread(
            target=self._run_single_thread,
            args=(prompt,),
            daemon=True,
        )
        thread.start()

    def _run_single_thread(self, prompt: str) -> None:
        try:
            self._set_status("⏳ Pipeline running…")
            output = self._pipeline.run(prompt)
            self._set_status(f"✅  Done → {output}")
            self._log(f"[bold green]🎉 Video saved to: {output}[/bold green]")
        except PipelineCancelled:
            self._set_status("⛔  Cancelled.")
            self._log("[yellow]Pipeline cancelled.[/yellow]")
        except Exception as e:
            self._set_status(f"❌  Error: {e}")
            self._log(f"[bold red]Error: {e}[/bold red]")
        finally:
            self._set_running(False)
            self._pipeline = None

    # ------------------------------------------------------------------
    # Multi-file markdown pipeline
    # ------------------------------------------------------------------

    def _start_files_pipeline(
        self, md_files: list[Path], use_placeholders: bool
    ) -> None:
        self._set_running(True)
        self._cancel_requested.clear()
        self._log("=" * 60)
        self._log(
            f"[bold]Mode:[/bold] Markdown files  "
            f"({len(md_files)} file{'s' if len(md_files) != 1 else ''})"
        )
        for f in md_files:
            self._log(f"[dim]  {f}[/dim]")
        if use_placeholders:
            self._log("[yellow]Test mode — placeholder images, no AI calls[/yellow]")
        else:
            has_hf = bool(self._config.hf_token)
            self._log(
                f"[dim]HF token: {'✓ found' if has_hf else '✗ missing — will use placeholders'}[/dim]"
            )
        self._log("=" * 60)
        self._log("")

        thread = threading.Thread(
            target=self._run_files_thread,
            args=(md_files, use_placeholders),
            daemon=True,
        )
        thread.start()

    def _run_files_thread(
        self, md_files: list[Path], use_placeholders: bool
    ) -> None:
        outputs: list[Path] = []
        errors: list[str] = []

        for idx, md_path in enumerate(md_files, 1):
            if self._cancel_requested.is_set():
                self._log("[yellow]Cancelled before processing remaining files.[/yellow]")
                break

            self._log(f"\n[bold blue]📄 File {idx}/{len(md_files)}: {md_path.name}[/bold blue]")
            self._set_status(f"⏳ File {idx}/{len(md_files)}: {md_path.name}")

            # Parse markdown
            try:
                md_text = md_path.read_text(encoding="utf-8")
                title, scenes = parse_markdown_story(md_text)
            except Exception as e:
                msg = f"Parse error in {md_path.name}: {e}"
                self._log(f"[red]  ✗ {msg}[/red]")
                errors.append(msg)
                continue

            if title:
                self._log(f"[dim]  Title: {title}[/dim]")
            self._log(f"[dim]  {len(scenes)} scenes found[/dim]")

            # Build and run pipeline — use title as prompt for music mood
            self._pipeline = Pipeline(
                config=self._config,
                progress_cb=self._log,
                use_placeholders=use_placeholders,
            )
            self._pipeline.inject_scenes(scenes)

            prompt_for_mood = title or md_path.stem.replace("_", " ").replace("-", " ")

            try:
                output = self._pipeline.run(prompt_for_mood)
                outputs.append(output)
                self._log(f"[bold green]  ✓ Video: {output}[/bold green]")
            except PipelineCancelled:
                self._log("[yellow]  Pipeline cancelled.[/yellow]")
                self._cancel_requested.set()
                break
            except Exception as e:
                msg = f"Pipeline error for {md_path.name}: {e}"
                self._log(f"[bold red]  ✗ {msg}[/bold red]")
                errors.append(msg)
            finally:
                self._pipeline = None

        # Summary
        self._log("\n" + "=" * 60)
        if outputs:
            self._log(
                f"[bold green]🎉 {len(outputs)}/{len(md_files)} video(s) generated:[/bold green]"
            )
            for out in outputs:
                self._log(f"[green]  {out}[/green]")
        if errors:
            self._log(f"[yellow]  {len(errors)} error(s):[/yellow]")
            for err in errors:
                self._log(f"[yellow]    • {err}[/yellow]")

        status = (
            f"✅  {len(outputs)}/{len(md_files)} done"
            if not self._cancel_requested.is_set()
            else f"⛔  Cancelled  ({len(outputs)} completed)"
        )
        self._set_status(status)
        self._set_running(False)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _resolve_md_paths(raw: str) -> list[Path]:
    """Expand a comma-separated path string into a sorted list of .md files."""
    files: list[Path] = []
    for entry in raw.split(","):
        p = Path(entry.strip()).expanduser().resolve()
        if p.is_dir():
            files.extend(sorted(p.glob("*.md")))
        elif p.is_file() and p.suffix.lower() == ".md":
            files.append(p)
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique
