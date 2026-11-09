@echo off
echo Starting Stella AI...
cd /d E:\Projects\stella

echo Starting all Stella endpoints together (backend + frontend)...
node scripts/start-all.js

echo Stella has been shut down.
echo Backend WebSocket: ws://127.0.0.1:8765
echo Frontend: http://localhost:3000
echo.
pause