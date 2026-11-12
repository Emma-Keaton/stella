# Cloudflare Tunnel Setup Script for Stella
# PowerShell version with automation

param(
    [switch]$Install,
    [switch]$Login,
    [switch]$CreateTunnel,
    [string]$TunnelName = "stella-backend",
    [switch]$Start
)

Write-Host "Cloudflare Tunnel Setup for Stella" -ForegroundColor Cyan
Write-Host ""

# Install cloudflared
if ($Install -or -not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "[1] Installing cloudflared..." -ForegroundColor Yellow
    choco install cloudflared -y
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Installation failed. Try: choco install cloudflared -y" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] cloudflared installed" -ForegroundColor Green
}

# Login
if ($Login) {
    Write-Host "[2] Opening Cloudflare login..." -ForegroundColor Yellow
    cloudflared tunnel login
}

# Create tunnel
if ($CreateTunnel) {
    Write-Host "[3] Creating tunnel: $TunnelName" -ForegroundColor Yellow
    cloudflared tunnel create $TunnelName
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Tunnel created" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "1. Note the tunnel ID from output above" -ForegroundColor White
        Write-Host "2. Create config file at $env:USERPROFILE\.cloudflared\config.yml" -ForegroundColor White
        Write-Host "3. Start tunnel with: cloudflared tunnel run $TunnelName" -ForegroundColor White
    }
}

# Start tunnel
if ($Start) {
    $configPath = "$env:USERPROFILE\.cloudflared\config.yml"
    if (-not (Test-Path $configPath)) {
        Write-Host "[ERROR] Config not found: $configPath" -ForegroundColor Red
        Write-Host "Create config file first!" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[4] Starting tunnel..." -ForegroundColor Yellow
    cloudflared tunnel run $TunnelName
}

Write-Host ""
Write-Host "After tunnel is running, you'll see URL like:" -ForegroundColor Cyan
Write-Host "  https://abc123.trycloudflare.com" -ForegroundColor White
Write-Host ""
Write-Host "Set Vercel env vars:" -ForegroundColor Yellow
Write-Host "  NEXT_PUBLIC_BACKEND_WS_URL=wss://abc123.trycloudflare.com" -ForegroundColor White
