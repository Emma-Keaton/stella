#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipLlama,
    [switch]$NoStart,
    [switch]$Dev,
    [int]$BackendPort = 8765,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = 'Stop'
$REPO_ROOT = Resolve-Path '.'
$LLAMA_DIR = Join-Path $REPO_ROOT 'llama-servers'
$BACKEND_DIR = $REPO_ROOT
$FRONTEND_DIR = Join-Path $REPO_ROOT 'frontend'
$VENV_DIR = Join-Path $BACKEND_DIR '.venv'
$VENV_PYTHON = Join-Path $VENV_DIR 'Scripts/python.exe'
$VENV_PYTHONW = Join-Path $VENV_DIR 'Scripts/pythonw.exe'

function Update-Environment {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Run-Cmd {
    param([string]$Cmd, [string[]]$Args, [string]$WorkingDir = $REPO_ROOT, [hashtable]$Env = $null)
    Write-Host "  [$WorkingDir] $Cmd $Args" -ForegroundColor Yellow
    $proc = Start-Process -FilePath $Cmd -ArgumentList $Args -WorkingDirectory $WorkingDir `
        -NoNewWindow -Wait -PassThru -RedirectStandardOutput $null -RedirectStandardError $null -Environment $Env
    if ($proc.ExitCode -ne 0) {
        Write-Host "  ERROR: $Cmd exited with code $($proc.ExitCode)" -ForegroundColor Red
        return $false
    }
    return $true
}

function Test-Command {
    param([string]$Name)
    return (Get-Command $Name -ErrorAction SilentlyContinue) -ne $null
}

# Self-elevate to Administrator
if (-not $IsElevated) {
    if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "Elevating privileges for installation..." -ForegroundColor Yellow
        $arguments = "& '" + $myinvocation.mycommand.definition + "' " + ($myinvocation.line -replace $myinvocation.mycommand.definition, '').Trim()
        Start-Process powershell -Verb runAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command $arguments"
        exit
    }
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Stella EVO - Unified Startup Script" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check/install Python
Write-Host ">>> 1/7: Checking Python..." -ForegroundColor Green
$PythonExe = $null
if (Test-Command "py") { $PythonExe = "py" }
elseif (Test-Command "python") { $PythonExe = "python" }

if (-not $PythonExe) {
    Write-Host "Python not found. Downloading Python 3.11.8..." -ForegroundColor Yellow
    $PythonUrl = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
    $PythonInstaller = "$env:TEMP\python_installer.exe"
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonInstaller -TimeoutSec 300
    Write-Host "Installing Python (Silent Mode)..." -ForegroundColor Yellow
    Start-Process -FilePath $PythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
    Write-Host "Python installed successfully." -ForegroundColor Green
    Update-Environment
    $PythonExe = "python"
} else {
    $pyVersion = & $PythonExe --version 2>&1
    Write-Host "Python already installed: $pyVersion ($(Get-Command $PythonExe | Select-Object -ExpandProperty Source))" -ForegroundColor Green
}

# 2. Check/install Node.js
Write-Host ">>> 2/7: Checking Node.js..." -ForegroundColor Green
if (-not (Test-Command "node")) {
    Write-Host "Node.js not found. Downloading Node v20 LTS..." -ForegroundColor Yellow
    $NodeUrl = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"
    $NodeInstaller = "$env:TEMP\node_installer.msi"
    Invoke-WebRequest -Uri $NodeUrl -OutFile $NodeInstaller -TimeoutSec 300
    Write-Host "Installing Node.js (Silent Mode)..." -ForegroundColor Yellow
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$NodeInstaller`" /qn" -Wait
    Write-Host "Node.js installed successfully." -ForegroundColor Green
    Update-Environment
} else {
    $nodeVersion = node --version 2>&1
    Write-Host "Node.js already installed: $nodeVersion ($(Get-Command node | Select-Object -ExpandProperty Source))" -ForegroundColor Green
}

# 3. Python virtual environment
Write-Host ">>> 3/7: Setting up Python virtual environment..." -ForegroundColor Green
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "Creating Virtual Environment in .venv..." -ForegroundColor Cyan
    if (Test-Path $VENV_DIR) { Remove-Item -Recurse -Force $VENV_DIR }
    Start-Process -FilePath $PythonExe -ArgumentList "-m venv .venv" -Wait -NoNewWindow
    Write-Host "Virtual Environment created." -ForegroundColor Green
# 4. Python dependencies
if (-not $SkipBackend) {
    Write-Host ">>> 4/7: Installing Python dependencies..." -ForegroundColor Green

    # Upgrade pip first
    Start-Process -FilePath $VENV_PYTHON -ArgumentList "-m pip install --upgrade pip setuptools wheel" -Wait -NoNewWindow

    # Install requirements-core (includes tiny-tts, pocket-tts, phonon-2, edge-tts, etc.)
    $reqCore = Join-Path $REPO_ROOT 'requirements/requirements-core.txt'
    if (Test-Path $reqCore) {
        Write-Host "    Installing requirements-core.txt ..." -ForegroundColor Cyan
        Run-Cmd -Cmd $VENV_PYTHON -Args @("-m", "pip", "install", "-r", $reqCore, "--ignore-requires-python")
    }

    # Install requirements-voice (additional voice packages)
    $reqVoice = Join-Path $REPO_ROOT 'requirements/requirements-voice.txt'
    if (Test-Path $reqVoice) {
        Write-Host "    Installing requirements-voice.txt ..." -ForegroundColor Cyan
        Run-Cmd -Cmd $VENV_PYTHON -Args @("-m", "pip", "install", "-r", $reqVoice, "--ignore-requires-python")
    }

    # Install requirements-all (everything else)
    $reqAll = Join-Path $REPO_ROOT 'requirements/requirements-all.txt'
    if (Test-Path $reqAll) {
        Write-Host "    Installing requirements-all.txt ..." -ForegroundColor Cyan
        Run-Cmd -Cmd $VENV_PYTHON -Args @("-m", "pip", "install", "-r", $reqAll, "--ignore-requires-python")
    }

    Write-Host "    Python dependencies ready." -ForegroundColor Green
}

# 5. Node.js frontend dependencies
if (-not $SkipFrontend) {
    Write-Host ">>> 5/7: Installing Node.js frontend dependencies..." -ForegroundColor Green
    if (-not (Test-Path Join-Path $FRONTEND_DIR 'package.json')) {
        Write-Host "  WARNING: frontend/package.json not found, skipping npm install" -ForegroundColor Yellow
    } else {
        Run-Cmd -Cmd 'npm' -Args @('install') -WorkingDir $FRONTEND_DIR
        Write-Host "    Frontend dependencies ready." -ForegroundColor Green
    }
}

} else {
    Write-Host "Virtual Environment already exists." -ForegroundColor Green
}

# 6. llama.cpp servers
if (-not $SkipLlama) {
    Write-Host ">>> 6/7: Downloading llama.cpp servers..." -ForegroundColor Green
    if (-not (Test-Path $LLAMA_DIR)) { New-Item -ItemType Directory -Path $LLAMA_DIR -Force | Out-Null }

    # mbuzai llama.cpp server
    $MbuzaiUrl = 'https://github.com/mbuzai/llama.cpp/releases/download/server-b5423/llama-b5423-bin-win-x64.zip'
    $MbuzaiZip = Join-Path $LLAMA_DIR 'mbuzai-server.zip'
    $MbuzaiDir = Join-Path $LLAMA_DIR 'mbuzai'

    if (-not (Test-Path $MbuzaiDir)) {
        Write-Host "    Downloading mbuzai llama.cpp server..."
        try {
            Invoke-WebRequest -Uri $MbuzaiUrl -OutFile $MbuzaiZip -TimeoutSec 600
            Expand-Archive -Path $MbuzaiZip -DestinationPath $LLAMA_DIR -Force
            Remove-Item $MbuzaiZip -Force
            Write-Host "    mbuzai server ready." -ForegroundColor Green
        } catch {
            Write-Host "  WARNING: Failed to download mbuzai server: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    mbuzai server already present." -ForegroundColor Green
    }

    # upstream/llama.cpp server (official ggerganov release)
    $UpstreamUrl = 'https://github.com/ggerganov/llama.cpp/releases/download/server-b5423/llama-b5423-bin-win-x64.zip'
    $UpstreamZip = Join-Path $LLAMA_DIR 'upstream-server.zip'
    $UpstreamDir = Join-Path $LLAMA_DIR 'upstream'

    if (-not (Test-Path $UpstreamDir)) {
        Write-Host "    Downloading upstream llama.cpp server..."
        try {
            Invoke-WebRequest -Uri $UpstreamUrl -OutFile $UpstreamZip -TimeoutSec 600
            Expand-Archive -Path $UpstreamZip -DestinationPath $LLAMA_DIR -Force
            Remove-Item $UpstreamZip -Force
            Write-Host "    upstream server ready." -ForegroundColor Green
        } catch {
            Write-Host "  WARNING: Failed to download upstream server: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    upstream server already present." -ForegroundColor Green
    }
}

# 7. Start servers
if (-not $NoStart) {
    Write-Host ">>> 7/7: Starting Stella servers..." -ForegroundColor Green

    # Start Python backend (WebSocket IPC on :8765)
    Write-Host "    Starting Stella backend (python main.py --host 0.0.0.0 --port $BackendPort)..." -ForegroundColor Green
    $env:PYTHONPATH = $BACKEND_DIR
    if ($Dev) {
        $env:STELLA_DEV_MODE = 'true'
        $env:NODE_ENV = 'development'
    } else {
        $env:STELLA_DEV_MODE = 'false'
        $env:NODE_ENV = 'production'
    }

    $backendProc = Start-Process -FilePath $VENV_PYTHONW -ArgumentList "main.py", "--host", "0.0.0.0", "--port", $BackendPort `
        -WorkingDirectory $BACKEND_DIR -NoNewWindow -PassThru

    # Give backend a moment to bind the port
    Start-Sleep -Seconds 3

    # Start Next.js frontend (dev server on :3000)
    if (-not $SkipFrontend) {
        Write-Host "    Starting Next.js frontend (npm run dev -- --port $FrontendPort)..." -ForegroundColor Green
        $npmArgs = @('run', 'dev', '--', '--port', $FrontendPort)
        if ($Dev) {
            $frontendEnv = @{ NODE_ENV = 'development'; BROWSER = 'none'; PORT = $FrontendPort.ToString() }
        } else {
            $frontendEnv = @{ NODE_ENV = 'production'; BROWSER = 'none'; PORT = $FrontendPort.ToString() }
        }
        $frontendProc = Start-Process -FilePath 'npm' -ArgumentList $npmArgs `
            -WorkingDirectory $FRONTEND_DIR -NoNewWindow -PassThru -Environment $frontendEnv
    }

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "   Stella is running!" -ForegroundColor Green
    Write-Host "   Backend WebSocket: ws://localhost:$BackendPort" -ForegroundColor Green
    if (-not $SkipFrontend) { Write-Host "   Frontend:          http://localhost:$FrontendPort" -ForegroundColor Green }
    Write-Host "   llama servers:     $LLAMA_DIR" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all servers." -ForegroundColor Yellow

    # Keep the script alive until user presses Ctrl+C
    try {
        while ($true) {
            if ($backendProc.HasExited) {
                Write-Host "Backend process exited unexpectedly." -ForegroundColor Red
                break
            }
            if (-not $SkipFrontend -and $frontendProc -and $frontendProc.HasExited) {
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
    if (-not $SkipFrontend -and $frontendProc) { try { $frontendProc.Kill() } catch {} }
    Write-Host "Stella stopped." -ForegroundColor Green
}

