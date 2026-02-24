#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎬 VidGen Setup & Launch"
echo "========================"

# 1. Check/install system dependencies
echo ""
echo "📦 Checking system dependencies..."

NEED_APT=()

PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '3\.\d+')
        minor=${ver#3.}
        if [ "$minor" -ge 10 ] 2>/dev/null; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ Python 3.10+ not found. Install with: sudo apt install python3.10 (or newer)"
    exit 1
fi

if ! $PYTHON -c "import venv" 2>/dev/null; then
    NEED_APT+=("${PYTHON}-venv")
fi

if ! command -v ffmpeg &>/dev/null; then
    NEED_APT+=("ffmpeg")
fi

if ! dpkg -s python3-full &>/dev/null 2>&1; then
    NEED_APT+=("python3-full")
fi

if [ ${#NEED_APT[@]} -gt 0 ]; then
    echo "⚙️  Installing: ${NEED_APT[*]}"
    sudo apt update -qq
    sudo apt install -y "${NEED_APT[@]}"
else
    echo "✅ System dependencies OK"
fi

# 2. Create/update virtual environment
echo ""
if [ ! -d ".venv" ]; then
    echo "🐍 Creating virtual environment..."
    $PYTHON -m venv .venv
else
    echo "✅ Virtual environment exists"
fi

source .venv/bin/activate

# 3. Install/update Python packages
echo ""
echo "📥 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q
echo "✅ Python dependencies installed"

# 4. Create output directory
mkdir -p output assets

# 5. Check HF token
echo ""
if [ -n "$HF_TOKEN" ]; then
    echo "🔑 HF_TOKEN found in environment"
elif [ -f "$HOME/.vidgen/config.json" ]; then
    echo "🔑 Config found at ~/.vidgen/config.json"
else
    echo "⚠️  No HF_TOKEN set. You can:"
    echo "   export HF_TOKEN=your_key_here"
    echo "   or save to ~/.vidgen/config.json"
    echo "   (Test mode works without a token)"
fi

# 6. Launch
echo ""
echo "🚀 Launching VidGen TUI..."
echo ""
python -m vidgen.main "$@"
