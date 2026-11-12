# Stella Complete Startup Script
# Starts Python Backend (WebSocket + Core + Agents + Skills), and Frontend
# PowerShell version for Windows

param(
    [switch]$Dev,
    [switch]$NoFrontend,
    [string]$BackendHost = "0.0.0.0",
    [int]$BackendPort = 8765,
    [int]$FrontendPort = 3000,
)

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    STELLA COMPLETE STARTUP                     ║" -ForegroundColor Cyan
Write-Host "║     Backend (WebSocket) │ Core │ Agents │ Skills               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$STELLA_DIR = "E:\Projects\stella"
$FRONTEND_DIR = "$STELLA_DIR\frontend"

# Check prerequisites
Write-Host "[INFO] Checking prerequisites..." -ForegroundColor White

if (!(Test-Path $STELLA_DIR)) {
    Write-Host "[ERROR] Stella directory not found: $STELLA_DIR" -ForegroundColor Red
    exit 1
}

# Set environment
if ($Dev) {
    $env:STELLA_DEV_MODE = "true"
    $env:NODE_ENV = "development"
    Write-Host "[WARNING] Running in DEVELOPMENT mode" -ForegroundColor Yellow
} else {
    $env:STELLA_DEV_MODE = "false"
    $env:NODE_ENV = "production"
    Write-Host "[SUCCESS] Running in PRODUCTION mode" -ForegroundColor Green
}


# Start Python Backend
Write-Host "[BACKEND] Starting Python Backend (WebSocket + Core + Agents + Skills)..." -ForegroundColor Magenta
Write-Host "   - WebSocket server on ${BackendHost}:$BackendPort" -ForegroundColor Magenta
Write-Host "   - StellaEngine core" -ForegroundColor Magenta
Write-Host "   - Agent system (CrewManager)" -ForegroundColor Magenta
Write-Host "   - Skills catalog" -ForegroundColor Magenta

$env:PYTHONPATH = $STELLA_DIR
$backendProcess = Start-Process -FilePath "python" -ArgumentList "main.py","--host",$BackendHost,"--port",$BackendPort -WorkingDirectory $STELLA_DIR -PassThru -WindowStyle Hidden

if ($backendProcess.Id) {
    Write-Host "[SUCCESS] Backend started with PID $($backendProcess.Id)" -ForegroundColor Green
}

Start-Sleep -Seconds 3

# Start Frontend
if (!$NoFrontend) {
    Write-Host "[FRONTEND] Starting Next.js Frontend..." -ForegroundColor Green
    if ($Dev) {
        Start-Process -FilePath "npm" -ArgumentList "run","dev","--","--port",$FrontendPort -WorkingDirectory $FRONTEND_DIR -WindowStyle Hidden
    } else {
        Start-Process -FilePath "npm" -ArgumentList "run","start","--","--port",$FrontendPort -WorkingDirectory $FRONTEND_DIR -WindowStyle Hidden
    }
    Write-Host "[SUCCESS] Frontend started on http://localhost:$FrontendPort" -ForegroundColor Green
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor White
Write-Host "[SUCCESS] All services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "[INFO] Services:" -ForegroundColor White
Write-Host "   Backend WebSocket:   ws://$BackendHost`:$BackendPort" -ForegroundColor Magenta
Write-Host "   Frontend:            http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host ""
Write-Host "[INFO] Components Connected:" -ForegroundColor White
Write-Host "   ✓ WebSocket IPC Server (main.py)" -ForegroundColor Green
Write-Host "   ✓ Stella Core Engine (StellaEngine)" -ForegroundColor Green
Write-Host "   ✓ Agent System (CrewManager)" -ForegroundColor Green
Write-Host "   ✓ Skills Catalog" -ForegroundColor Green
Write-Host "   ✓ StarNet Integrations" -ForegroundColor Green
Write-Host "   ✓ Memory Manager" -ForegroundColor Green
Write-Host "   ✓ Config Manager" -ForegroundColor Green
Write-Host ""
Write-Host "[WARNING] Press Ctrl+C to stop all services" -ForegroundColor Yellow

try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-Host "[WARNING] Shutting down services..." -ForegroundColor Yellow
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
Write-Host "[SUCCESS] Services stopped" -ForegroundColor Green
}
