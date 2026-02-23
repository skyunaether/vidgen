"""Batch-generate videos from markdown story files.

Usage:
    python batch_stories.py                        # interactive path prompt
    python batch_stories.py path/to/stories/       # directory of .md files
    python batch_stories.py story1.md story2.md    # specific files
    python batch_stories.py "stories/*.md"         # glob pattern
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vidgen.batchutil import resolve_md_paths
from vidgen.config import Config
from vidgen.pipeline import Pipeline, PipelineCancelled
from vidgen.scriptgen import parse_markdown_story


def _prompt_for_paths() -> list[Path]:
    """Interactively ask the user for a path when none are provided."""
    print("No paths provided. Enter one of:")
    print("  • A directory containing .md files  (e.g. stories/)")
    print("  • One or more .md file paths        (space/comma-separated)")
    print("  • A glob pattern                    (e.g. stories/*.md)")
    print()
    raw = input("Path(s): ").strip()
    if not raw:
        print("No input given. Exiting.")
        sys.exit(0)
    # Split on both space and comma for flexibility
    sep = "," if "," in raw else " "
    return resolve_md_paths(raw, sep=sep)


def main() -> None:
    # Collect .md files from CLI args or interactive prompt
    if len(sys.argv) > 1:
        # CLI args: join with commas, let resolve_md_paths handle it
        raw_args = ",".join(sys.argv[1:])
        md_files = resolve_md_paths(raw_args, sep=",")
    else:
        md_files = _prompt_for_paths()

    if not md_files:
        print("No .md files found. Exiting.")
        sys.exit(1)

    config = Config.load()
    use_placeholders = not config.hf_token
    if use_placeholders:
        print("WARNING: No HF_TOKEN — using placeholders (images will be grey)")

    print(f"\nFound {len(md_files)} story file(s)\n")

    ok = 0
    failed = 0

    for idx, md_path in enumerate(md_files, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(md_files)}] {md_path.name}")
        print(f"{'='*60}")

        try:
            text = md_path.read_text(encoding="utf-8")
            title, scenes, settings = parse_markdown_story(text)
            print(f"  Title : {title or '(untitled)'}")
            print(f"  Scenes: {len(scenes)}, ~{sum(s.duration for s in scenes):.0f}s total")
            print(f"  Music : {settings.music_style}")
            print(f"  Voice : {settings.voice} (rate {settings.voice_rate}, pitch {settings.voice_pitch})")
        except Exception as e:
            print(f"  ERROR (parse): {e}")
            failed += 1
            continue

        pipeline = Pipeline(
            config=config,
            progress_cb=lambda msg: print(f"  {msg}"),
            use_placeholders=use_placeholders,
        )
        pipeline.inject_scenes(scenes, settings=settings)

        try:
            output = pipeline.run(title or md_path.stem)
            print(f"\n  Saved: {output}")
            ok += 1
        except PipelineCancelled:
            print("  Cancelled by user.")
            break
        except Exception as e:
            print(f"  ERROR (pipeline): {e}")
            failed += 1
            continue

    print(f"\n{'='*60}")
    print(f"Done: {ok} succeeded, {failed} failed.")


if __name__ == "__main__":
    main()
