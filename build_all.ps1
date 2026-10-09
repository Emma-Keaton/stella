param(
    [switch]$SkipInstaller = $false
)

Write-Host "Building Stella Evo Application..." -ForegroundColor Cyan
# PyInstaller may be installed in .venv without its console-script shim;
# `python -m PyInstaller` needs no shim, so prefer what actually exists.
$VenvPy = ".\.venv\Scripts\python.exe"
$PyInstallerExe = ".\.venv\Scripts\pyinstaller.exe"
if (Test-Path $PyInstallerExe) {
    $PYI = @($PyInstallerExe)
} elseif (Test-Path $VenvPy) {
    $PYI = @($VenvPy, "-m", "PyInstaller")
} else {
    Write-Host "No .venv found. Create it first and install requirements (includes pyinstaller)." -ForegroundColor Red
    exit 1
}
& $VenvPy -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "pyinstaller not found in .venv. Run bootstrap.ps1 first." -ForegroundColor Red
    exit 1
}

# 1. Main application (collect-mode; produces dist\StellaEvo\)
& $PYI installer\Stella.spec --noconfirm

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
& $PYI installer\Stella_Setup.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build setup wizard!" -ForegroundColor Red
    exit 1
}

Write-Host "Build complete! Setup is located in dist\StellaEvo_Setup.exe" -ForegroundColor Green
