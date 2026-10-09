# build.ps1 — one command to build Stella on any host (Windows).
# Thin wrapper over scripts/stella_build.py so the muscle memory matches
# macOS/Linux. All arguments pass straight through.
#
#   .\build.ps1 --plan
#   .\build.ps1 --edition lite --os windows --release
#   .\build.ps1 --edition full --os android
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "No .venv. Create it first:" -ForegroundColor Red
    Write-Host "  py -3 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller"
    exit 1
}

& $py "scripts\stella_build.py" @Args
exit $LASTEXITCODE
