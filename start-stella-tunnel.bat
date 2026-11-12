@echo off
setlocal

echo ========================================
echo Stella Cloudflare Tunnel Startup
echo ========================================
echo.

set STELLA_DIR=E:\Projects\stella
set TUNNEL_NAME=stella-backend

echo [1] Starting Stella Backend...
start "Stella Backend" powershell -NoExit -Command "cd /d %STELLA_DIR% && python main.py --host 0.0.0.0 --port 8765"

timeout /t 5 /nobreak >nul

echo [2] Starting Cloudflare Tunnel...
echo.
echo Tunnel will be available at:
echo   https://*.trycloudflare.com
echo.
echo Starting tunnel... Press Ctrl+C to stop
echo.

cloudflared tunnel run %TUNNEL_NAME%

echo.
echo Tunnel stopped
pause
