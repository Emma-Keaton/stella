@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Stella Evo - Launcher
cd /d "%~dp0"

color 0E

echo ____ _____ _____ _     _        _      _______     _____  
echo / ___^|_   _^| ____^| ^|   ^| ^|      / \    ^| ____\ \   / / _ \ 
echo \___ \ ^| ^| ^|  _^| ^| ^|   ^| ^|     / _ \   ^|  _^|  \ \ / / ^| ^| ^|
echo  ___) ^|^| ^| ^| ^|___^| ^|___^| ^|___ / ___ \  ^| ^|___  \ V /^| ^|_^| ^|
echo ^|____/ ^|_^| ^|_____^|_____^|_____/_/   \_\ ^|_____^|  \_/  \___/
echo ==========================================================================
echo.
echo Launching automated bootstrap sequence...

powershell.exe -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"

if %errorlevel% neq 0 (
  echo ERROR: Bootstrap failed.
  pause
  exit /b %errorlevel%
)
exit /b 0
