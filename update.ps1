# update.ps1 — update an installed Stella to the latest published version.
# Uses scripts/stella_update.py (manifest-driven, resumable, SHA-256 verified).
#
#   .\update.ps1              # check + update if newer
#   .\update.ps1 --check      # only report versions
#   .\update.ps1 -InstallDir "C:\Program Files\Stella"
param(
    [switch]$Check,
    [string]$InstallDir = "",
    [string]$ManifestUrl = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }   # fall back to system python

$call = @()
if ($Check)        { $call += "--check" }
if ($InstallDir)   { $call += @("--install-dir", $InstallDir) }
if ($ManifestUrl)  { $call += @("--manifest-url", $ManifestUrl) }
$call += $Rest

& $py "scripts\stella_update.py" @call
exit $LASTEXITCODE
