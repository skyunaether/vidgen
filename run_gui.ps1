# VidGen Web UI launcher
# Usage: .\run_gui.ps1          # production (serves built frontend)
#        .\run_gui.ps1 -Dev     # dev mode (Vite HMR on :5173, backend on :8000)

param(
    [switch]$Dev
)

$RepoRoot    = $PSScriptRoot
$Venv        = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python      = if (Test-Path $Venv) { $Venv } else { "python" }
$FrontendDir = Join-Path $RepoRoot "webui\frontend"
$Dist        = Join-Path $FrontendDir "dist"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  VidGen Web UI" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# -- Free ports if already occupied -------------------------------------------
function Stop-Port {
    param([int]$Port)
    $pids = (netstat -ano | Select-String ":$Port\s.*LISTENING") |
            ForEach-Object { ($_ -split '\s+')[-1] } |
            Select-Object -Unique
    foreach ($p in $pids) {
        if ($p -match '^\d+$') {
            Write-Host "   Killing PID $p on port $Port" -ForegroundColor DarkGray
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}

Stop-Port 8000
if ($Dev) { Stop-Port 5173 }

# -- Dev mode -----------------------------------------------------------------
if ($Dev) {
    Write-Host ">> Mode: Development (hot reload)" -ForegroundColor Yellow
    Write-Host ""

    Write-Host ">> Starting backend on http://localhost:8000 ..." -ForegroundColor Green
    $backend = Start-Process -FilePath $Python `
        -ArgumentList "-m", "uvicorn", "webui.backend.app:app", "--reload", "--port", "8000" `
        -WorkingDirectory $RepoRoot `
        -PassThru -NoNewWindow

    Write-Host ">> Starting Vite dev server on http://localhost:5173 ..." -ForegroundColor Green
    $frontend = Start-Process -FilePath "npm" `
        -ArgumentList "run", "dev" `
        -WorkingDirectory $FrontendDir `
        -PassThru -NoNewWindow

    Start-Sleep -Seconds 3
    $url = "http://localhost:5173"

# -- Production mode ----------------------------------------------------------
} else {
    Write-Host ">> Mode: Production" -ForegroundColor Green
    Write-Host ""

    if (-not (Test-Path $Dist)) {
        Write-Host ">> Building frontend (first run) ..." -ForegroundColor Yellow
        Push-Location $FrontendDir
        npm run build
        Pop-Location
        Write-Host ""
    }

    Write-Host ">> Starting backend on http://localhost:8000 ..." -ForegroundColor Green
    $backend = Start-Process -FilePath $Python `
        -ArgumentList "-m", "uvicorn", "webui.backend.app:app", "--port", "8000" `
        -WorkingDirectory $RepoRoot `
        -PassThru -NoNewWindow

    $frontend = $null
    Start-Sleep -Seconds 2
    $url = "http://localhost:8000"
}

# -- Open browser -------------------------------------------------------------
Write-Host ""
Write-Host "[ OK ] Opening $url" -ForegroundColor Cyan
Start-Process $url

Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

# -- Wait and clean up --------------------------------------------------------
try {
    $backend.WaitForExit()
} finally {
    Write-Host ""
    Write-Host "Shutting down..." -ForegroundColor Yellow
    if ($backend  -and -not $backend.HasExited)  { $backend.Kill() }
    if ($frontend -and -not $frontend.HasExited) { $frontend.Kill() }
}
