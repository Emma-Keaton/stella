@echo off
cd /d "%~dp0"
set TAURI_BUILD=1
call npm run export
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
call npm run tauri:build