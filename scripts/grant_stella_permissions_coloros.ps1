#!/usr/bin/env pwsh
# Slim permission-grant helper for OPPO / ColorOS devices.
# ColorOS blocks `pm grant` and `appops set` for adb shell (uid 2000), so this
# script launches the relevant system-settings intents for manual toggle and
# verifies what is actually granted via dumpsys.
#
# Usage:
#   .\grant_stella_permissions_coloros.ps1 [-Package com.stella.connect.k2] [-Adb "C:\...\adb.exe"]

[CmdletBinding()]
param(
    [string]$Package = "com.stella.connect.k2",
    [string]$Adb = "C:\Users\USER\.stella-toolchain\android-sdk\platform-tools\adb.exe"
)

$env:PATH = "C:\Users\USER\.stella-toolchain\android-sdk\platform-tools;$env:PATH"
if (-not (Test-Path $Adb)) { throw "adb not found at $Adb" }

function Invoke-Adb($args) {
    & $Adb $args
}

function Launch-Settings($action, $data = $null, $label) {
    Write-Host ">> $label"
    $cmd = "shell am start -a `"$action`""
    if ($data) { $cmd += " -d `"$data`" " }
    Invoke-Adb $cmd | Out-Null
    Start-Sleep -Seconds 1
}

Write-Host "=== Stella ColorOS permission helper ==="
Write-Host "Package: $Package"
Write-Host ""

# 1. Draw over other apps (SYSTEM_ALERT_WINDOW) — HUD overlay
Launch-Settings "android.settings.action.MANAGE_OVERLAY_PERMISSION" "package:$Package" "SYSTEM_ALERT_WINDOW (HUD overlay)"

# 2. All-files access (MANAGE_EXTERNAL_STORAGE) — .gguf import
Launch-Settings "android.settings.action.MANAGE_ALL_FILES_ACCESS_PERMISSION" $null "MANAGE_EXTERNAL_STORAGE (all files)"

# 3. Battery optimization exemption — background engine persistence
Launch-Settings "android.settings.action.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" "package:$Package" "Battery optimization exemption"

# 4. App details — runtime dangerous permissions (mic, camera, location, notifications)
Launch-Settings "android.settings.action.APP_DETAILS_SETTINGS" "package:$Package" "App details (RECORD_AUDIO, CAMERA, LOCATION, NOTIFICATIONS)"

Write-Host ""
Write-Host "=== Toggle the above on the phone, then press Enter to verify ==="
Read-Host

Write-Host ""
Write-Host "=== Verification: granted runtime/special permissions ==="
$out = Invoke-Adb "shell dumpsys package $Package" 2>&1
$out | Select-String "RECORD_AUDIO|CAMERA|POST_NOTIFICATIONS|ACCESS_FINE_LOCATION|ACCESS_COARSE_LOCATION|SYSTEM_ALERT_WINDOW|MANAGE_EXTERNAL_STORAGE|FOREGROUND_SERVICE" | Select-Object -First 30

Write-Host ""
Write-Host "=== Verification: device idle whitelist ==="
Invoke-Adb "shell dumpsys deviceidle whitelist" | Select-String $Package

Write-Host ""
Write-Host "Done. If anything shows as not granted, re-open the corresponding setting on the phone."
