"""Batch-generate videos from markdown story files.

Usage:
    python batch_stories.py                        # interactive path prompt
    python batch_stories.py path/to/stories/       # directory of .md files
    python batch_stories.py story1.md story2.md    # specific files
    python batch_stories.py "stories/*.md"         # glob pattern
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vidgen.config import Config
from vidgen.pipeline import Pipeline, PipelineCancelled
from vidgen.scriptgen import parse_markdown_story


def _resolve_paths(args: list[str]) -> list[Path]:
    """Resolve CLI args to a sorted list of .md file paths."""
    paths: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.md")))
        else:
            # Expand shell globs (useful on Windows where the shell doesn't)
            expanded = glob.glob(arg, recursive=True)
            if expanded:
                for ep in sorted(expanded):
                    ep = Path(ep)
                    if ep.suffix.lower() == ".md" and ep.is_file():
                        paths.append(ep)
            elif p.suffix.lower() == ".md" and p.is_file():
                paths.append(p)
            elif p.suffix.lower() == ".md":
                print(f"  WARNING: file not found: {p}")
            else:
                print(f"  WARNING: skipping non-.md argument: {arg}")
    return paths


def _prompt_for_paths() -> list[Path]:
    """Interactively ask the user for a path when none are provided."""
    print("No paths provided. Enter one of:")
    print("  • A directory containing .md files  (e.g. stories/)")
    print("  • One or more .md file paths        (space-separated)")
    print("  • A glob pattern                    (e.g. stories/*.md)")
    print()
    raw = input("Path(s): ").strip()
    if not raw:
        print("No input given. Exiting.")
        sys.exit(0)
    return _resolve_paths(raw.split())


def main() -> None:
    args = sys.argv[1:]

    # Collect .md files
    if args:
        md_files = _resolve_paths(args)
    else:
        md_files = _prompt_for_paths()

    if not md_files:
        print("No .md files found. Exiting.")
        sys.exit(1)

    # Deduplicate while preserving order
    seen: set[Path] = set()
    md_files = [f for f in md_files if not (f in seen or seen.add(f))]

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
            title, scenes = parse_markdown_story(text)
            print(f"  Title : {title or '(untitled)'}")
            print(f"  Scenes: {len(scenes)}, ~{sum(s.duration for s in scenes):.0f}s total")
        except Exception as e:
            print(f"  ERROR (parse): {e}")
            failed += 1
            continue

        pipeline = Pipeline(
            config=config,
            progress_cb=lambda msg: print(f"  {msg}"),
            use_placeholders=use_placeholders,
        )
        pipeline.inject_scenes(scenes)

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
