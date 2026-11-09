#requires -Version 5.1
<#
.SYNOPSIS
    Stella Setup & Launch Script

.DESCRIPTION
    One-stop setup for Stella:
      1. Installs Python backend dependencies
      2. Installs Node.js frontend dependencies
      3. Downloads llama.cpp servers (mbuzai + upstream builds)
      4. Builds the Next.js frontend
      5. Starts backend + frontend and keeps them alive until Ctrl+C

.PARAMETER SkipBackend
    Skip Python dependency installation
.PARAMETER SkipFrontend
    Skip Node.js dependency installation and build
.PARAMETER SkipLlama
    Skip llama.cpp server downloads
.PARAMETER NoStart
    Perform setup only; do not start servers
#>
[CmdletBinding()]
param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipLlama,
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
$REPO_ROOT = Resolve-Path '.'
$LLAMA_DIR = Join-Path $REPO_ROOT 'llama-servers'
$BACKEND_DIR = $REPO_ROOT
$FRONTEND_DIR = Join-Path $REPO_ROOT 'frontend'

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Stella Setup & Launch Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Run-Cmd {
    param([string]$Cmd, [string[]]$Args, [string]$WorkingDir = $REPO_ROOT)

    Write-Host "[$WorkingDir] $Cmd $Args" -ForegroundColor Yellow
    $proc = Start-Process -FilePath $Cmd -ArgumentList $Args -WorkingDirectory $WorkingDir `
        -NoNewWindow -Wait -PassThru -RedirectStandardOutput $null -RedirectStandardError $null
    if ($proc.ExitCode -ne 0) {
        Write-Host "  ERROR: $Cmd exited with code $($proc.ExitCode)" -ForegroundColor Red
        return $false
    }
    return $true
}

# ---------------------------------------------------------------------------
# 1. Backend dependencies
# ---------------------------------------------------------------------------
if (-not $SkipBackend) {
    Write-Host ">>> 1/5: Installing Python backend dependencies..." -ForegroundColor Green
    if (-not (Test-Path Join-Path $REPO_ROOT 'requirements')) {
        Write-Host "  WARNING: requirements/ folder not found, skipping pip install" -ForegroundColor Yellow
    } else {
        $reqFiles = Get-ChildItem -Path Join-Path $REPO_ROOT 'requirements' -Filter '*.txt' -Name
        foreach ($rf in $reqFiles) {
            $rfPath = Join-Path $REPO_ROOT 'requirements' $rf
            Write-Host "    Installing $rf ..."
            if (-not (Run-Cmd -Cmd 'pip' -Args @("install", "-r", $rfPath))) {
                Write-Host "  Failed to install $rf" -ForegroundColor Red
            }
        }
    }
    Write-Host "    Backend dependencies ready." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 2. Frontend dependencies + build
# ---------------------------------------------------------------------------
if (-not $SkipFrontend) {
    Write-Host ">>> 2/5: Installing Node.js frontend dependencies..." -ForegroundColor Green
    if (-not (Test-Path Join-Path $FRONTEND_DIR 'package.json')) {
        Write-Host "  WARNING: frontend/package.json not found, skipping npm install" -ForegroundColor Yellow
    } else {
        if (-not (Run-Cmd -Cmd 'npm' -Args @('install') -WorkingDir $FRONTEND_DIR)) {
            Write-Host "  npm install failed" -ForegroundColor Red
        }
    }

    Write-Host ">>> 3/5: Building Next.js frontend..." -ForegroundColor Green
    if (-not (Run-Cmd -Cmd 'npm' -Args @('run', 'build') -WorkingDir $FRONTEND_DIR)) {
        Write-Host "  npm run build failed" -ForegroundColor Red
    }
    Write-Host "    Frontend ready." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 3. Download llama.cpp servers (mbuzai + upstream)
# ---------------------------------------------------------------------------
if (-not $SkipLlama) {
    Write-Host ">>> 4/5: Downloading llama.cpp servers..." -ForegroundColor Green
    if (-not (Test-Path $LLAMA_DIR)) {
        New-Item -ItemType Directory -Path $LLAMA_DIR -Force | Out-Null
    }

    # mbuzai/llama.cpp server (Windows x64)
    $MbuzaiUrl = 'https://github.com/mbuzai/llama.cpp/releases/download/server-llama-3.2/server-llama-win-x64.zip'
    $MbuzaiZip = Join-Path $LLAMA_DIR 'mbuzai-server.zip'
    $MbuzaiDir = Join-Path $LLAMA_DIR 'mbuzai'

    if (-not (Test-Path $MbuzaiDir)) {
        Write-Host "    Downloading mbuzai llama.cpp server..."
        try {
            Invoke-WebRequest -Uri $MbuzaiUrl -OutFile $MbuzaiZip -TimeoutSec 300
            Expand-Archive -Path $MbuzaiZip -DestinationPath $LLAMA_DIR -Force
            Remove-Item $MbuzaiZip -Force
            Write-Host "    mbuzai server ready." -ForegroundColor Green
        } catch {
            Write-Host "    WARNING: Failed to download mbuzai server: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    mbuzai server already present." -ForegroundColor Green
    }

    # upstream/llama.cpp server (official release)
    $UpstreamUrl = 'https://github.com/ggerganov/llama.cpp/releases/download/server-b5423/llama-b5423-bin-win-x64.zip'
    $UpstreamZip = Join-Path $LLAMA_DIR 'upstream-server.zip'
    $UpstreamDir = Join-Path $LLAMA_DIR 'upstream'

    if (-not (Test-Path $UpstreamDir)) {
        Write-Host "    Downloading upstream llama.cpp server..."
        try {
            Invoke-WebRequest -Uri $UpstreamUrl -OutFile $UpstreamZip -TimeoutSec 300
            Expand-Archive -Path $UpstreamZip -DestinationPath $LLAMA_DIR -Force
            Remove-Item $UpstreamZip -Force
            Write-Host "    upstream server ready." -ForegroundColor Green
        } catch {
            Write-Host "    WARNING: Failed to download upstream server: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    upstream server already present." -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# 4. Start servers
# ---------------------------------------------------------------------------
if (-not $NoStart) {
    Write-Host ">>> 5/5: Starting Stella servers..." -ForegroundColor Green

    # Start Python backend (WebSocket IPC on :8765)
    Write-Host "    Starting Stella backend (python main.py)..." -ForegroundColor Green
    $backendProc = Start-Process -FilePath 'python' -ArgumentList @('main.py') -WorkingDirectory $BACKEND_DIR `
        -NoNewWindow -PassThru

    # Give backend a moment to bind the port
    Start-Sleep -Seconds 3

    # Start Next.js frontend (dev server on :3000)
    Write-Host "    Starting Next.js frontend (npm run dev)..." -ForegroundColor Green
    $frontendProc = Start-Process -FilePath 'npm' -ArgumentList @('run', 'dev') -WorkingDirectory $FRONTEND_DIR `
        -NoNewWindow -PassThru

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   Stella is running!" -ForegroundColor Green
    Write-Host "   Backend WebSocket: ws://localhost:8765" -ForegroundColor Green
    Write-Host "   Frontend:          http://localhost:3000" -ForegroundColor Green
    Write-Host "   llama servers:     $LLAMA_DIR" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all servers." -ForegroundColor Yellow

    # Keep the script alive until user presses Ctrl+C
    try {
        while ($true) {
            # Check if either process exited
            if ($backendProc.HasExited) {
                Write-Host "Backend process exited unexpectedly." -ForegroundColor Red
                break
            }
            if ($frontendProc.HasExited) {
                Write-Host "Frontend process exited unexpectedly." -ForegroundColor Red
                break
            }
            Start-Sleep -Seconds 2
        }
    } catch {
        # Ctrl+C was pressed
    }

    # Cleanup child processes on exit
    Write-Host ""
    Write-Host "Shutting down Stella servers..." -ForegroundColor Yellow
    try { $backendProc.Kill() } catch {}
    try { $frontendProc.Kill() } catch {}
    Write-Host "Stella stopped." -ForegroundColor Green
}