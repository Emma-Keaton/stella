@echo off
setlocal

echo ========================================
echo Cloudflare Tunnel Setup for Stella
echo ========================================
echo.

echo [1] Installing cloudflared...
choco install cloudflared -y

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Installation failed
    pause
    exit /b 1
)

echo.
echo [2] Cloudflared installed successfully!
echo.
echo Next steps:
echo.
echo 1. Login to Cloudflare:
echo    cloudflared tunnel login
echo.
echo 2. Create tunnel:
echo    cloudflared tunnel create stella-backend
echo.
echo 3. Note the tunnel ID from output
echo.
echo 4. Create config file:
echo    mkdir %%USERPROFILE%%\.cloudflared
echo    notepad %%USERPROFILE%%\.cloudflared\config.yml
echo.
echo 5. Add config:
echo    tunnel: stella-backend
echo    credentials-file: %%USERPROFILE%%\.cloudflared\*.json
echo    ingress:
echo      - hostname: stella-backend.trycloudflare.com
echo        service: http://localhost:8765
echo      - service: http_status:404
echo.
echo 6. Start tunnel:
echo    cloudflared tunnel run stella-backend
echo.
echo 7. Copy the URL for Vercel env vars
echo.

pause
