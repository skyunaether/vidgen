"""Entry point for vidgen TUI."""
from __future__ import annotations

import logging
import sys
import asyncio
from pathlib import Path

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _setup_logging() -> None:
    log_dir = Path.home() / ".vidgen"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_dir / "vidgen.log"),
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run_headless(prompt: str, use_placeholders: bool = False) -> None:
    """Run the pipeline without the TUI, printing progress to stdout."""
    from .config import Config
    from .pipeline import Pipeline, PipelineCancelled

    config = Config.load()

    if not config.hf_token and not use_placeholders:
        print("⚠  No HF_TOKEN found — switching to placeholder mode.")
        use_placeholders = True

    def progress(msg: str) -> None:
        print(msg)

    pipeline = Pipeline(config=config, progress_cb=progress, use_placeholders=use_placeholders)
    try:
        output = pipeline.run(prompt)
        print(f"\n✅ Output: {output}")
    except PipelineCancelled:
        print("Cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main() -> None:
    """Launch VidGen — TUI by default, headless with --prompt."""
    _setup_logging()

    args = sys.argv[1:]

    # Headless mode: python -m vidgen.main --prompt "..." [--test]
    if "--prompt" in args:
        idx = args.index("--prompt")
        if idx + 1 >= len(args):
            print("Usage: --prompt <text> [--test]")
            sys.exit(1)
        prompt = args[idx + 1]
        use_placeholders = "--test" in args
        run_headless(prompt, use_placeholders=use_placeholders)
        return

    from .tui import VidGenApp

    app = VidGenApp()
    app.run()


if __name__ == "__main__":
    main()
