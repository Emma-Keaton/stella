param(
    [string]$Log = "build_apk_k2.log",
    [string]$Done = "build_apk_k2.done",
    [string]$Apk = "stella-connect-android\app\build\outputs\apk\release\stella-k2-bundled-arm64.apk",
    [int]$TimeoutMin = 25
)

$Root = "E:\Projects\stella"
$LogPath = Join-Path $Root $Log
$DonePath = Join-Path $Root $Done
$ApkPath = Join-Path $Root $Apk

if (Test-Path $DonePath) { Remove-Item $DonePath -Force }

$start = Get-Date
while (((Get-Date) - $start).TotalMinutes -lt $TimeoutMin) {
    $done = $false
    $msg = ""
    if (Test-Path $LogPath) {
        $tail = Get-Content $LogPath -Tail 3 -ErrorAction SilentlyContinue
        if ($tail -match "BUILD SUCCESSFUL") { $done = $true; $msg = "BUILD SUCCESSFUL" }
        elseif ($tail -match "FAILED|error:|Exception") { $done = $true; $msg = "BUILD FAILED: $($tail -join ' | ')" }
    }
    if (-not $done -and (Test-Path $ApkPath)) {
        $age = (Get-Date) - (Get-Item $ApkPath).LastWriteTime
        if ($age.TotalMinutes -lt 2) { $done = $false }  # fresh APK, wait for log confirm
    }
    if ($done) {
        "$(Get-Date -Format 'HH:mm:ss') $msg" | Out-File $DonePath -Encoding UTF8
        exit 0
    }
    Start-Sleep -Seconds 20
}
"$(Get-Date -Format 'HH:mm:ss') TIMEOUT after ${TimeoutMin} min" | Out-File $DonePath -Encoding UTF8
exit 1
