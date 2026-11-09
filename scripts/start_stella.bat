@echo off
echo Starting Stella AI...
cd E:\Projects\stella

echo Starting backend...
start "Stella Backend" cmd /k "python main.py"

timeout /t 2

echo Starting dashboard...
start "Stella Dashboard" cmd /k "cd dashboard && python server.py"

echo Stella is starting...
echo Backend: ws://127.0.0.1:8765
echo Dashboard: http://localhost:8000
pause