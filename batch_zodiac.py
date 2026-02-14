"""Batch-generate videos from the zodiac-stories markdown files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vidgen.config import Config
from vidgen.pipeline import Pipeline, PipelineCancelled
from vidgen.scriptgen import parse_markdown_story

STORIES_DIR = Path(__file__).parent.parent / "zodiac-stories"

def main():
    config = Config.load()
    use_placeholders = not config.hf_token
    if use_placeholders:
        print("⚠  No HF_TOKEN — using placeholders")

    md_files = sorted(STORIES_DIR.glob("*.md"))
    print(f"Found {len(md_files)} story files\n")

    for idx, md_path in enumerate(md_files, 1):
        print(f"\n{'='*60}")
        print(f"📄 [{idx}/{len(md_files)}] {md_path.name}")
        print(f"{'='*60}")

        try:
            text = md_path.read_text()
            title, scenes = parse_markdown_story(text)
            print(f"  Title: {title}")
            print(f"  Scenes: {len(scenes)}, ~{sum(s.duration for s in scenes):.0f}s")
        except Exception as e:
            print(f"  ✗ Parse error: {e}")
            continue

        pipeline = Pipeline(
            config=config,
            progress_cb=lambda msg: print(f"  {msg}"),
            use_placeholders=use_placeholders,
        )
        pipeline.inject_scenes(scenes)

        try:
            output = pipeline.run(title or md_path.stem)
            print(f"\n  ✅ Saved: {output}")
        except PipelineCancelled:
            print("  Cancelled.")
            break
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

if __name__ == "__main__":
    main()
