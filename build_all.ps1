param(
    [switch]$SkipInstaller = $false
)

Write-Host "Building Stella Evo Application..." -ForegroundColor Cyan
if (-not (Test-Path ".\.venv\Scripts\pyinstaller.exe")) {
    Write-Host "pyinstaller not found in .venv. Run bootstrap.ps1 first." -ForegroundColor Red
    exit 1
}

# 1. Main application (collect-mode; produces dist\StellaEvo\)
.\.venv\Scripts\pyinstaller.exe installer\Stella.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build main application!" -ForegroundColor Red
    exit 1
}

if ($SkipInstaller) {
    Write-Host "Main app built. Setup wizard skipped (-SkipInstaller)." -ForegroundColor Yellow
    exit 0
}

Write-Host "Main Application built successfully. Now building Setup Wizard..." -ForegroundColor Cyan
# 2. Setup wizard (one-file; embeds dist\StellaEvo\ as its payload)
.\.venv\Scripts\pyinstaller.exe installer\Stella_Setup.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build setup wizard!" -ForegroundColor Red
    exit 1
}

Write-Host "Build complete! Setup is located in dist\StellaEvo_Setup.exe" -ForegroundColor Green
