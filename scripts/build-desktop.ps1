# build-desktop.ps1 — one command to build the Stella DESKTOP app (native window, not a browser tab).
#
# Pipeline:
#   1. PyInstaller -> dist/stella-backend/  (Python backend as a standalone exe folder)
#   2. copy it as the Tauri sidecar binary  frontend/src-tauri/binaries/stella-backend-<target>.exe
#   3. npm run export                        (Next.js static export -> frontend/out)
#   4. npx tauri build                       (native app + MSI/NSIS installer)
#
# Output: frontend/src-tauri/target/release/bundle/msi/Stella_*.msi  (Windows installer)
#         frontend/src-tauri/target/release/stella-desktop.exe     (portable exe)
#
# Dev mode (no packaging):  npm run tauri:dev   (runs `next dev` + opens the native
# window; backend starts via `python main.py` fallback in main.rs)

param(
    # Rust target triple for the native build. Default = MinGW (small download,
    # metered-data friendly). Use x86_64-pc-windows-msvc if VS Build Tools installed.
    [string]$Target = 'x86_64-pc-windows-gnu'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root 'frontend'
$Tauri = Join-Path $Frontend 'src-tauri'

Write-Host '== 1/4 Building Python backend (PyInstaller onedir) ==' -ForegroundColor Cyan
$VenvPy = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $VenvPy)) { $VenvPy = 'python' }
& $VenvPy -m PyInstaller --noconfirm --clean --name stella-backend --onedir --distpath (Join-Path $Root 'dist') `
    --add-data "$(Join-Path $Root 'core');core" `
    --add-data "$(Join-Path $Root 'agent');agent" `
    --add-data "$(Join-Path $Root 'src');src" `
    --add-data "$(Join-Path $Root 'skills');skills" `
    --add-data "$(Join-Path $Root 'memory');memory" `
    --add-data "$(Join-Path $Root 'models');models" `
    --hidden-import websockets --hidden-import psutil --hidden-import cactus `
    (Join-Path $Root 'main.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller backend build failed' }

Write-Host '== 2/4 Installing backend as Tauri sidecar ==' -ForegroundColor Cyan
$Binaries = Join-Path $Tauri 'binaries'
New-Item -ItemType Directory -Force -Path $Binaries | Out-Null
# Tauri 2 sidecar naming: <name>-<target-triple>[.exe]
$SidecarDir = Join-Path $Binaries "stella-backend-$Target"
Remove-Item -Recurse -Force $SidecarDir -ErrorAction SilentlyContinue
Copy-Item -Recurse (Join-Path $Root 'dist\stella-backend') $SidecarDir
Write-Host "   sidecar -> $SidecarDir"

Write-Host '== 3/4 Static-exporting Next.js frontend ==' -ForegroundColor Cyan
Push-Location $Frontend
npm run export
if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'next export failed' }

Write-Host "== 4/4 Building native desktop app (Tauri, target $Target) ==" -ForegroundColor Cyan
npx @tauri-apps/cli build -- --target $Target
$Code = $LASTEXITCODE
Pop-Location
if ($Code -ne 0) { throw 'tauri build failed' }

Write-Host ''
Write-Host 'DESKTOP BUILD COMPLETE' -ForegroundColor Green
Write-Host "  Installer : $Tauri\target\release\bundle\msi\*.msi"
Write-Host "  Portable  : $Tauri\target\release\stella-desktop.exe"
Write-Host 'Run the installer (or the exe) — the app starts its own backend on ws://127.0.0.1:8765.'
