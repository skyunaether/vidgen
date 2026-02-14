# 📖 VidGen User Guide

> **Automated AI Video Generation Pipeline**
> Turn a text prompt into a YouTube Shorts-ready video in minutes.

---

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Setup & Installation](#setup--installation)
4. [Configuration](#configuration)
5. [Getting Started](#getting-started)
6. [Project Architecture](#project-architecture)
7. [Pipeline Stages Explained](#pipeline-stages-explained)
8. [TUI Controls & Interface](#tui-controls--interface)
9. [Example Use Cases](#example-use-cases)
10. [Output Specifications](#output-specifications)
11. [Tips & Best Practices](#tips--best-practices)
12. [Troubleshooting](#troubleshooting)
13. [FAQ](#faq)

---

## Overview

**VidGen** is a Python-based video generation pipeline that takes a simple text prompt and produces a complete 2-minute vertical video optimized for YouTube Shorts. It combines:

- 🤖 **AI Image Generation** — via Hugging Face Inference API (Flux.1-dev / SDXL)
- 🎬 **AI Video Generation** — via Stable Video Diffusion for animated scenes
- 🎞️ **Intelligent Compilation** — ffmpeg handles transitions, effects, overlays
- 📺 **Interactive TUI** — real-time progress tracking in your terminal

The entire workflow is automated: prompt in → video out.

---

## System Requirements

| Requirement | Details |
|---|---|
| **OS** | Linux (Ubuntu/Debian tested), macOS, WSL2 |
| **Python** | 3.12 (recommended) |
| **ffmpeg** | Required for video compilation |
| **RAM** | 4GB minimum, 8GB+ recommended |
| **Disk** | ~500MB per generated video (temp files cleaned after) |
| **Network** | Required for HF API calls (not needed in test mode) |
| **HF Account** | Free tier works; Pro subscription recommended for faster inference |

---

## Setup & Installation

### One-Command Setup

The included `run.sh` script handles everything automatically:

```bash
cd /home/yun/.openclaw/workspace/vidgen
./run.sh
```

**What `run.sh` does:**
1. ✅ Checks for Python 3.12, ffmpeg, python3-full
2. 📦 Installs missing system packages via `apt` (asks for sudo password once)
3. 🐍 Creates a Python virtual environment (`.venv/`)
4. 📥 Installs all Python dependencies
5. 📁 Creates `output/` and `assets/` directories
6. 🔑 Checks for HF API token
7. 🚀 Launches the TUI

### Manual Setup (if you prefer)

```bash
# 1. Install system dependencies
sudo apt install -y python3.12-venv ffmpeg python3-full

# 2. Navigate to project
cd /home/yun/.openclaw/workspace/vidgen

# 3. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 4. Install Python packages
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 5. Create directories
mkdir -p output assets

# 6. Run
python -m vidgen.main
```

---

## Configuration

### Hugging Face API Token

You need a Hugging Face token for real AI generation. Get one at: https://huggingface.co/settings/tokens

**Option A: Environment Variable (recommended)**
```bash
export HF_TOKEN="hf_your_token_here"
./run.sh
```

To make it permanent, add to your `~/.bashrc`:
```bash
echo 'export HF_TOKEN="hf_your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**Option B: Config File**
```bash
mkdir -p ~/.vidgen
cat > ~/.vidgen/config.json << 'EOF'
{
  "hf_token": "hf_your_token_here"
}
EOF
```

### Full Config Options

`~/.vidgen/config.json` supports:

```json
{
  "hf_token": "hf_your_token_here",
  "bg_music": "/path/to/background_music.mp3",
  "output_dir": "/custom/output/path"
}
```

| Key | Description | Default |
|---|---|---|
| `hf_token` | Hugging Face API token | `""` (test mode) |
| `bg_music` | Path to background music file (MP3/WAV) | `null` (no music) |
| `output_dir` | Where to save generated videos | `./output/` |

### AI Models Used

| Stage | Primary Model | Fallback |
|---|---|---|
| Image Generation | `black-forest-labs/FLUX.1-dev` | `stabilityai/stable-diffusion-xl-base-1.0` |
| Video Generation | `stabilityai/stable-video-diffusion-img2vid-xt` | ffmpeg placeholder animation |

---

## Getting Started

### Your First Video (Test Mode)

No API key needed! Test mode generates placeholder images to verify the full pipeline works:

1. Run `./run.sh`
2. Type any prompt (e.g., "A journey through space")
3. Click **🧪 Test (Placeholders)**
4. Watch the progress log as each stage runs
5. Find your video in `output/`

### Your First Real Video

1. Set your HF token (see [Configuration](#configuration))
2. Run `./run.sh`
3. Enter a descriptive prompt
4. Click **🚀 Generate**
5. Wait for AI image/video generation (~3-10 minutes depending on API load)
6. Video saved to `output/vidgen_YYYYMMDD_HHMMSS.mp4`

---

## Project Architecture

```
vidgen/
├── run.sh                  # 🚀 One-command setup & launch
├── pyproject.toml          # Package metadata & dependencies
├── requirements.txt        # Pip requirements
├── README.md               # Quick reference
├── USERGUIDE.md            # This guide
├── vidgen/
│   ├── __init__.py         # Package init
│   ├── main.py             # Entry point — launches TUI
│   ├── tui.py              # Textual TUI app (UI, buttons, progress log)
│   ├── pipeline.py         # Orchestrator — runs all stages in sequence
│   ├── scriptgen.py        # Template-based scene breakdown generator
│   ├── imagegen.py         # HF image generation (Flux/SDXL)
│   ├── videogen.py         # HF video generation (Stable Video Diffusion)
│   ├── compiler.py         # ffmpeg compilation (Ken Burns, transitions, overlays)
│   └── config.py           # Settings, API key management, constants
├── output/                 # Generated videos land here
├── assets/                 # Background music, custom fonts, etc.
└── .venv/                  # Python virtual environment (auto-created)
```

### Data Flow

```
User Prompt
    │
    ▼
┌─────────────┐
│  scriptgen   │  → Breaks prompt into ~11 timed scenes (JSON)
└──────┬──────┘
       ▼
┌─────────────┐
│  imagegen    │  → Generates an image for each scene via HF API
└──────┬──────┘
       ▼
┌─────────────┐
│  videogen    │  → Animates selected scenes (type: "video") via HF API
└──────┬──────┘
       ▼
┌─────────────┐
│  compiler    │  → Stitches everything with ffmpeg (effects, overlays)
└──────┬──────┘
       ▼
   output.mp4   (1080×1920, ~2 min, H.264+AAC)
```

---

## Pipeline Stages Explained

### Stage 1: Script Generation (`scriptgen.py`)

Takes your prompt and generates a structured scene breakdown.

- **Extracts the topic** from your prompt (strips "create a video about…" prefixes)
- **Picks a template** based on keyword matching:
  - 🌿 **Nature** — triggered by: nature, animal, wildlife, ocean, forest, mountain
  - 💻 **Tech** — triggered by: tech, AI, robot, computer, software, code, digital
  - 🎬 **Default** — used for everything else
- **Generates ~11 scenes**, each with:
  - `narration` — text overlay for the scene
  - `visual` — detailed image generation prompt
  - `duration` — seconds (8-12s per scene)
  - `media_type` — `"image"` (static + Ken Burns) or `"video"` (AI animated)
- **Targets ~120 seconds** total, auto-adjusting durations

### Stage 2: Image Generation (`imagegen.py`)

Generates an image for every scene using the HF Inference API.

- **Primary model**: Flux.1-dev (high quality, detailed)
- **Fallback**: SDXL (if Flux fails or is unavailable)
- **Resolution**: 1080×1920 (vertical, Shorts-ready)
- **Retries**: Up to 3 attempts per image with exponential backoff
- **Test mode**: Generates colored placeholder images with scene text

### Stage 3: Video Generation (`videogen.py`)

Animates scenes marked as `media_type: "video"` (typically 2-3 per video).

- **Model**: Stable Video Diffusion img2vid-xt
- Takes the generated image and produces a ~4-second video clip
- **Fallback**: If API fails, falls back to ffmpeg-based gentle animation
- Only processes "video" type scenes; "image" scenes use Ken Burns in compilation

### Stage 4: Compilation (`compiler.py`)

The heavy lifting — combines everything into the final video using ffmpeg.

- **Ken Burns Effect**: Gentle 8% zoom on static images (creates movement)
- **Crossfade Transitions**: 0.5-second fade between every scene
- **Text Overlays**: White text with dark shadow, positioned in the bottom third
- **Background Music**: Mixed in if configured (auto-ducked under narration text)
- **Output**: H.264 video + AAC audio, 30fps, 1080×1920 MP4
- **Cleanup**: Temp files removed after successful compilation

---

## TUI Controls & Interface

```
┌─────────────────────────────────────────┐
│  Enter a video prompt:                  │
│  ┌─────────────────────────────────┐    │
│  │ e.g., Create a video about...   │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ⚠ No HF_TOKEN found...                │
│                                         │
│  [🚀 Generate] [⛔ Cancel] [🧪 Test]   │
│                                         │
│  Progress log area...                   │
│  > Generating script...                 │
│  > Scene 1/11: Generating image...      │
│  > ...                                  │
│                                         │
│  ─────── Status Bar ──────              │
└─────────────────────────────────────────┘
```

### Controls

| Action | How |
|---|---|
| Enter prompt | Type in the text field |
| Generate (with AI) | Click **🚀 Generate** or press Enter |
| Test (placeholders) | Click **🧪 Test (Placeholders)** |
| Cancel generation | Click **⛔ Cancel** or press `Ctrl+C` |
| Quit | Press `Ctrl+Q` |

### Progress Log

The log shows real-time updates:
- Script generation progress
- Image generation per scene (with model info)
- Video generation for animated scenes
- Compilation steps
- Final output path

---

## Example Use Cases

### 1. Nature Documentary Short
```
Prompt: "The mysterious deep ocean and its bioluminescent creatures"
```
**Result**: 11-scene video with underwater imagery, ecosystem shots, conservation messaging. Uses the nature template with aerial shots, macro details, and sunrise finale.

### 2. Tech Explainer
```
Prompt: "How artificial intelligence is transforming healthcare"
```
**Result**: Tech-themed video with futuristic UI visuals, data visualizations, conference shots, and cyberpunk-aesthetic future predictions.

### 3. Travel Content
```
Prompt: "Beautiful hidden temples of Bali Indonesia"
```
**Result**: Default template with cinematic establishing shots, close-up architectural details, historical context, and golden-hour finale.

### 4. Educational Content
```
Prompt: "The science behind black holes and event horizons"
```
**Result**: Space-themed video with dramatic cosmic imagery, scientific visualizations, and awe-inspiring finale.

### 5. Product/Brand Awareness
```
Prompt: "Sustainable fashion and eco-friendly clothing brands"
```
**Result**: Modern lifestyle video with product shots, infographic-style impact stats, and hopeful future outlook.

### 6. Motivational/Inspirational
```
Prompt: "The power of daily habits and how small changes transform lives"
```
**Result**: Warm, personal video with contemplative shots, real-world examples, and inspiring conclusion.

---

## Output Specifications

| Property | Value |
|---|---|
| **Resolution** | 1080 × 1920 (9:16 vertical) |
| **Format** | MP4 |
| **Video Codec** | H.264 |
| **Audio Codec** | AAC |
| **Frame Rate** | 30 fps |
| **Duration** | ~2 minutes (114-124 seconds) |
| **Transitions** | 0.5s crossfade between scenes |
| **Text** | White with shadow, bottom third |
| **File Location** | `output/vidgen_YYYYMMDD_HHMMSS.mp4` |
| **Typical File Size** | 50-150 MB |

---

## Tips & Best Practices

### Writing Better Prompts

1. **Be specific** — "The aurora borealis over Norwegian fjords" beats "northern lights"
2. **Include the subject clearly** — The system extracts your topic from the prompt
3. **Use keywords that match templates** — Including "ocean", "AI", "forest" etc. triggers specialized scene structures
4. **Keep it concise** — One clear topic per video works best

### Getting Better Results

1. **Use HF Pro subscription** — Faster inference, fewer rate limits, better model access
2. **Run during off-peak hours** — HF API is faster when less busy (early morning UTC)
3. **Test first** — Always do a test run to preview the script before burning API credits
4. **Add background music** — Videos feel 10x more professional with music. Drop an MP3 in `assets/` and set `bg_music` in config

### Optimizing for YouTube Shorts

1. **Hook in first 3 seconds** — The opening scene should be visually striking
2. **Keep text readable** — Narration overlays are designed for mobile viewing
3. **Vertical format** — Already optimized at 1080×1920
4. **Under 60 seconds for Shorts** — If you want true Shorts, modify `TARGET_DURATION` in `scriptgen.py` to `60`
5. **Add captions** — Consider using a captioning tool on the output for accessibility

### Performance Tips

1. **First run is slowest** — Subsequent runs reuse the venv
2. **API rate limits** — If you hit HF rate limits, the retry logic handles it (waits and retries up to 3 times)
3. **Disk space** — Each video generates ~200MB of temp files (auto-cleaned)
4. **Cancel gracefully** — Use the Cancel button or Ctrl+C; don't kill the terminal (temp files won't clean up)

---

## Troubleshooting

### "externally-managed-environment" error
**Cause**: Running pip outside the virtual environment.
**Fix**: Always use `./run.sh` which handles the venv automatically.

### "python3.12-venv not found"
**Fix**: `sudo apt install python3.12-venv`

### "ffmpeg not found"
**Fix**: `sudo apt install ffmpeg`

### HF API timeout or 503 errors
**Cause**: HF servers are busy or model is loading (cold start).
**Fix**: The retry logic handles this automatically (3 retries with delay). If persistent, try again later or during off-peak hours.

### "No HF_TOKEN found" warning
**Cause**: Token not set.
**Fix**: See [Configuration](#configuration). You can still use **Test mode** without a token.

### Video has no audio
**Cause**: No background music configured.
**Fix**: Add a music file to config:
```json
{ "bg_music": "/path/to/music.mp3" }
```

### Black frames in output
**Cause**: Image generation failed for some scenes.
**Fix**: Check internet connection and HF token validity. Look at the progress log for specific error messages.

### TUI doesn't display properly
**Cause**: Terminal doesn't support the Textual UI framework.
**Fix**: Use a modern terminal (GNOME Terminal, Kitty, Alacritty, iTerm2). Minimum 80×24 terminal size.

---

## FAQ

**Q: How long does generation take?**
A: Test mode: ~30 seconds. Real AI generation: 3-10 minutes depending on HF API speed and your subscription tier.

**Q: Does it cost money?**
A: HF free tier has rate limits but works. HF Pro ($9/mo) gives faster/more reliable inference. No other costs.

**Q: Can I change the video duration?**
A: Yes — edit `TARGET_DURATION` in `vidgen/scriptgen.py` (default: 120 seconds). For YouTube Shorts, set to 60.

**Q: Can I add my own templates?**
A: Yes — add entries to the `_TEMPLATES` list in `vidgen/scriptgen.py`. Each template has `keywords` (for matching) and `scenes` (the scene list).

**Q: Can I use a different image model?**
A: Yes — change `PRIMARY_IMAGE_MODEL` and `FALLBACK_IMAGE_MODEL` in `vidgen/config.py`.

**Q: Where are temp files stored?**
A: In your system's temp directory. They're automatically cleaned up after successful compilation.

**Q: Can I reuse generated images?**
A: Currently they're in temp dirs and cleaned up. To keep them, you'd need to modify `pipeline.py` to copy them to a permanent location before cleanup.

**Q: Will LLM-based script generation be added?**
A: Yes — the `scriptgen.py` module is designed with a swap-in architecture. A future update will use HF text generation models for dynamic, prompt-aware scene scripts instead of templates.

---

## What's Next

Planned improvements:
- 🧠 **LLM Script Generation** — Dynamic scene breakdowns using HF text models
- 🗣️ **AI Voiceover** — Text-to-speech narration via HF API
- 🎵 **Auto Background Music** — Generate or select music based on video mood
- ✂️ **Scene Editor** — Preview and rearrange scenes in the TUI before generation
- 📊 **Analytics** — Track generation stats, API usage, and costs

---

*Last updated: 2026-02-13*
*VidGen — Made with 🎬 and 🤖*
