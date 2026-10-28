#!/usr/bin/env pwsh
# scripts/portable/portable_stella.ps1 — self-contained Stella launcher (Windows).
#
# Runs Stella from a fully portable layout: the .venv next to this script, the
# repo root as the working directory, and Stella's user data dir under the
# portable storage folder so nothing is written outside the bundle.
#
# Usage:
#   .\scripts\portable\portable_stella.ps1
#   .\scripts\portable\portable_stella.ps1 --windowed   # pythonw, no console

param(
    [switch]$Windowed,
    [string]$DataDir
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..\..")

# Resolve the Python interpreter: prefer the venv next to this script.
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    $py = Join-Path $repoRoot ".venv\Scripts\pythonw.exe"
}
if (-not (Test-Path $py)) {
    Write-Host "No .venv found at $repoRoot\.venv. Run bootstrap first." -ForegroundColor Red
    exit 1
}

# Portable user data: everything Stella writes stays under the portable data dir.
if ($DataDir) {
    $dataDir = Resolve-Path $DataDir -ErrorAction SilentlyContinue
    if (-not $dataDir) { $dataDir = Resolve-Path (Join-Path $scriptDir "data") }
} else {
    $dataDir = Resolve-Path (Join-Path $scriptDir "data")
}
$dataDir = $dataDir | Select-Object -ExpandProperty Path
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

# Force Stella's user-data dir into the portable location.
$env:STELLA_USER_DATA_DIR = $dataDir
$env:LOCALAPPDATA = $dataDir

# Set the working directory to the repo so relative imports resolve.
Set-Location $repoRoot | Out-Null

# Pick the entry point.
$exe = "main.py"
if ($Windowed) {
    $pyw = Join-Path $repoRoot ".venv\Scripts\pythonw.exe"
    if (Test-Path $pyw) { $py = $pyw }
}

Write-Host "Stella (portable) starting from $repoRoot" -ForegroundColor Cyan
Write-Host "User data dir : $dataDir" -ForegroundColor Cyan

& $py $exe
exit $LASTEXITCODE
