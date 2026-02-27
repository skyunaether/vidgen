<#
.SYNOPSIS
Runs the Multi-Agent Video Generation Orchestrator.

.DESCRIPTION
This script sets up the environment and calls the Python orchestrator
to run the iterative generation and QC loop.

.PARAMETER prompt
The video prompt for the ProjectManager agent.

.PARAMETER maxIterations
Maximum number of iteratons (default: 3)
#>

param(
    [Parameter(Mandatory = $false)]
    [string]$prompt = "story",
    
    [Parameter(Mandatory = $false)]
    [string]$story,

    [Parameter(Mandatory = $false)]
    [int]$maxIterations = 3
)

$ErrorActionPreference = "Stop"

if (-not $env:HF_TOKEN) {
    Write-Warning "HF_TOKEN environment variable is not set. Hugging Face models will fail."
}

Write-Host "Starting Orchestrator..." -ForegroundColor Cyan

# Use python from active env, or fallback to python
$pyCmd = "python"
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pyCmd = "py" # Fallback if standard python isn't in path, but usually python is fine in venvs
}

$cmdArgs = @("--prompt", $prompt, "--max-iterations", $maxIterations)
if ($story) {
    $cmdArgs += "--story", $story
}

& $pyCmd -m orchestrator @cmdArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Orchestrator failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

Write-Host "Orchestrator finished successfully." -ForegroundColor Green
