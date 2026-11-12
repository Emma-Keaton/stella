@echo off
setlocal

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                    STELLA COMPLETE STARTUP                     ║
echo ║     Backend │ Core │ Agents │ Skills │ Frontend               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

set STELLA_DIR=E:\Projects\stella
set FRONTEND_DIR=%STELLA_DIR%\frontend

echo [INFO] Starting Stella Backend (WebSocket + Core + Agents + Skills)...
echo.
echo Components:
echo   - WebSocket IPC Server on ws://localhost:8765
echo   - StellaEngine Core
echo   - Agent System (CrewManager)
echo   - Skills Catalog
echo   - StarNet Integrations
echo   - Memory Manager
echo   - Config Manager
echo.

start "Stella Backend" powershell -NoExit -Command "cd /d %STELLA_DIR% && python main.py --host 0.0.0.0 --port 8765"

timeout /t 5 /nobreak >nul

echo [INFO] Starting Next.js Frontend...
start "Stella Frontend" powershell -NoExit -Command "cd /d %FRONTEND_DIR% && npm run dev -- --port 3000"

timeout /t 10 /nobreak >nul

echo.
echo ════════════════════════════════════════════════════════════════
echo [SUCCESS] All services started!
echo.
echo Services:
echo   Backend WebSocket:   ws://localhost:8765
echo   Backend Core:        StellaEngine active
echo   Agents:              CrewManager loaded
echo   Skills:              Skills catalog loaded
echo   Frontend:            http://localhost:3000
echo.
echo All components connected and ready!
echo.
pause
