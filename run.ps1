# VidGen Setup & Launch for Windows
# Run with: powershell -ExecutionPolicy Bypass -File run.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "VidGen Setup & Launch" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# 1. Check Python 3.12
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Checking system dependencies..." -ForegroundColor Yellow

$PYTHON = $null
foreach ($cmd in @("python3.12", "python3", "python")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.1[2-9]|Python 3\.[2-9]\d") {
            $PYTHON = $cmd
            break
        }
    } catch { }
}

if (-not $PYTHON) {
    Write-Host "ERROR: Python 3.12+ not found." -ForegroundColor Red
    Write-Host "  Download from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  Make sure to check 'Add Python to PATH' during install." -ForegroundColor Red
    exit 1
}

$pyver = & $PYTHON --version 2>&1
Write-Host "OK  $pyver found ($PYTHON)" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 2. Check ffmpeg
# ---------------------------------------------------------------------------
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "WARNING: ffmpeg not found in PATH." -ForegroundColor Yellow
    Write-Host "  Install options:" -ForegroundColor Yellow
    Write-Host "    winget install Gyan.FFmpeg" -ForegroundColor White
    Write-Host "    choco install ffmpeg        (if you have Chocolatey)" -ForegroundColor White
    Write-Host "    scoop install ffmpeg         (if you have Scoop)" -ForegroundColor White
    Write-Host "  Or download from https://ffmpeg.org/download.html" -ForegroundColor White
    Write-Host "  (You can still run in test/placeholder mode without ffmpeg)" -ForegroundColor Yellow
} else {
    $ffver = (ffmpeg -version 2>&1 | Select-Object -First 1) -replace "ffmpeg version ",""
    Write-Host "OK  ffmpeg found ($ffver)" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 3. Create / reuse virtual environment
# ---------------------------------------------------------------------------
Write-Host ""
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $PYTHON -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "OK  Virtual environment exists" -ForegroundColor Green
}

$pip    = ".\.venv\Scripts\pip.exe"
$python = ".\.venv\Scripts\python.exe"

# ---------------------------------------------------------------------------
# 4. Install / update Python packages
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
& $pip install --upgrade pip setuptools wheel -q
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: pip upgrade failed (non-fatal)" -ForegroundColor Yellow }

& $pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install requirements." -ForegroundColor Red
    exit 1
}
Write-Host "OK  Python dependencies installed" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 5. Create output / assets directories
# ---------------------------------------------------------------------------
foreach ($dir in @("output", "assets")) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
}

# ---------------------------------------------------------------------------
# 6. Check HF token
# ---------------------------------------------------------------------------
Write-Host ""
$configPath = "$env:USERPROFILE\.vidgen\config.json"
if ($env:HF_TOKEN) {
    Write-Host "HF_TOKEN found in environment" -ForegroundColor Green
} elseif (Test-Path $configPath) {
    Write-Host "Config found at $configPath" -ForegroundColor Green
} else {
    Write-Host "WARNING: No HF_TOKEN set. You can:" -ForegroundColor Yellow
    Write-Host "  `$env:HF_TOKEN = 'your_key_here'   (current session)" -ForegroundColor White
    Write-Host "  [System.Environment]::SetEnvironmentVariable('HF_TOKEN','your_key','User')" -ForegroundColor White
    Write-Host "  or save to $configPath" -ForegroundColor White
    Write-Host "  (Test mode works without a token)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 7. Launch
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Launching VidGen TUI..." -ForegroundColor Cyan
Write-Host ""
& $python -m vidgen.main @args
