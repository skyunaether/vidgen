# VidGen — Automated Video Generation Pipeline

Generate YouTube Shorts-style vertical videos (1080×1920) from text prompts.

## Quick Start

```bash
# Install dependencies
pip install -e .
# or
pip install -r requirements.txt

# Set your HuggingFace API token (optional — without it, placeholder images are used)
export HF_TOKEN="hf_your_token_here"

# Requires ffmpeg
sudo apt install ffmpeg  # or brew install ffmpeg

# Run the TUI
python -m vidgen.main
# or if installed:
vidgen
```

## Pipeline Stages

1. **Script Generation** — Breaks your prompt into ~11 scenes with narration, visual descriptions, and timing (~2 min total)
2. **Image Generation** — Generates images via HuggingFace Inference API (FLUX.1-dev with SDXL fallback)
3. **Video Generation** — Animates key scenes using Stable Video Diffusion (img2vid)
4. **Compilation** — FFmpeg stitches everything with Ken Burns effects, text overlays, crossfade transitions

## TUI Controls

- Enter prompt and press **Generate** (or Enter)
- **Test (Placeholders)** — runs the full pipeline with placeholder images (no API needed)
- **Cancel** (Ctrl+C) — stops the pipeline
- **Quit** (Ctrl+Q)

## Configuration

Set `HF_TOKEN` via environment variable or `~/.vidgen/config.json`:

```json
{
  "hf_token": "hf_your_token",
  "bg_music": "/path/to/music.mp3"
}
```

## Output

Videos are saved to `output/` with timestamp filenames: `vidgen_20260213_071400.mp4`

## Requirements

- Python 3.10+
- ffmpeg (in PATH)
- HuggingFace API token (for real image/video generation)
