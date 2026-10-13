<#
.SYNOPSIS
    Grant every permission Stella needs, from your PC, without root.

.DESCRIPTION
    Android has no API that lets an app grant its own dangerous permissions -
    deliberately, for user control. The supported way to do it in bulk is
    `adb shell pm grant`, which runs as the shell user rather than the app.
    That requires USB debugging (or wireless ADB) and works on an ordinary,
    unrooted phone.

    This script grants the runtime ("dangerous") permissions automatically and
    prints the exact taps needed for the three special permissions that no
    tool can grant: all-files access, display-over-other-apps, and
    screen-capture consent.

    The app itself still offers a one-tap "Grant all" button and never forces
    setup - this is a convenience for your own devices, not a requirement.

.PARAMETER Package
    Application id to target. Defaults to the public build id. Use
    'com.stella.connect.k2' for your personal K2 build.

.PARAMETER Serial
    Target a specific device, e.g. 'R58M123ABC'. Omit when only one is
    connected.

.PARAMETER Revoke
    Undo everything this script granted.

.EXAMPLE
    .\scripts\grant_stella_permissions.ps1
    .\scripts\grant_stella_permissions.ps1 -Package com.stella.connect.k2
    .\scripts\grant_stella_permissions.ps1 -Package com.stella.connect.k2 -Revoke
#>
[CmdletBinding()]
param(
    [string]$Package = 'com.stella.connect',
    [string]$Serial,
    [switch]$Revoke
)

$ErrorActionPreference = 'Stop'

# Runtime permissions, grouped so the output reads as intent rather than a
# wall of identifiers.
$groups = [ordered]@{
    'Camera + microphone'  = @('android.permission.CAMERA', 'android.permission.RECORD_AUDIO')
    'Notifications'        = @('android.permission.POST_NOTIFICATIONS')
    'Location'             = @('android.permission.ACCESS_COARSE_LOCATION',
                              'android.permission.ACCESS_FINE_LOCATION',
                              'android.permission.ACCESS_BACKGROUND_LOCATION')
    'Photos + media'       = @('android.permission.READ_MEDIA_IMAGES',
                              'android.permission.READ_MEDIA_VIDEO',
                              'android.permission.READ_MEDIA_AUDIO',
                              'android.permission.READ_EXTERNAL_STORAGE',
                              'android.permission.WRITE_EXTERNAL_STORAGE')
    'Nearby devices'       = @('android.permission.BLUETOOTH_CONNECT',
                              'android.permission.BLUETOOTH_SCAN')
}

function Find-Adb {
    $onPath = Get-Command adb -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        "$env:USERPROFILE\.stella-toolchain\android-sdk\platform-tools\adb.exe"
    ) | Where-Object { Test-Path $_ }
    if ($candidates) { return $candidates[0] }
    return $null
}

$adb = Find-Adb
if (-not $adb) {
    Write-Host "adb not found. Install Android platform-tools, or:" -ForegroundColor Red
    Write-Host "  winget install Google.PlatformTools" -ForegroundColor Yellow
    exit 1
}
Write-Host "adb: $adb" -ForegroundColor DarkGray

$adbArgs = @()
if ($Serial) { $adbArgs += @('-s', $Serial) }

function Invoke-Adb {
    param([string[]]$A)
    & $adb @adbArgs @A
}

# --- is the device there? --------------------------------------------------
$devices = Invoke-Adb @('devices') | Select-Object -Skip 1 |
    Where-Object { $_ -match '\tdevice$' }
if (-not $devices) {
    Write-Host "No device connected." -ForegroundColor Red
    Write-Host ""
    Write-Host "On the phone:" -ForegroundColor Yellow
    Write-Host "  1. Settings > About phone > tap Build number 7 times"
    Write-Host "  2. Settings > Developer options > USB debugging ON"
    Write-Host "  3. Plug in the cable and accept the USB debugging prompt"
    exit 1
}
Write-Host "device: $($devices -join ', ')" -ForegroundColor Green

# --- is the app installed? -------------------------------------------------
$found = Invoke-Adb @('shell', 'pm', 'list', 'packages', $Package)
if ($found -notmatch [regex]::Escape($Package)) {
    Write-Host "Package '$Package' is not installed on this device." -ForegroundColor Red
    Write-Host "Install the APK first, then re-run." -ForegroundColor Yellow
    exit 1
}

$apiLevel = [int]((Invoke-Adb @('shell', 'getprop', 'ro.build.version.sdk')) -join '').Trim()

# --- grant / revoke --------------------------------------------------------
$ok = 0; $skipped = 0; $failed = @()

foreach ($group in $groups.Keys) {
    Write-Host ""
    Write-Host $group -ForegroundColor Cyan
    foreach ($perm in $groups[$group]) {
        # Permissions introduced after this device's API level cannot be granted.
        if ($perm -match 'POST_NOTIFICATIONS' -and $apiLevel -lt 33) { $skipped++; continue }
        if ($perm -match 'READ_MEDIA_' -and $apiLevel -lt 33) { $skipped++; continue }
        if ($perm -match 'BLUETOOTH_(CONNECT|SCAN)' -and $apiLevel -lt 31) { $skipped++; continue }
        if ($perm -match 'ACCESS_BACKGROUND_LOCATION' -and $apiLevel -lt 29) { $skipped++; continue }

        if ($Revoke) {
            $out = Invoke-Adb @('shell', 'pm', 'revoke', $Package, $perm) 2>&1
            if ($LASTEXITCODE -eq 0) { Write-Host "  revoked $($perm.Split('.')[-1])" -ForegroundColor DarkGray }
        } else {
            Invoke-Adb @('shell', 'pm', 'grant', $Package, $perm) 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  granted $($perm.Split('.')[-1])" -ForegroundColor Green
                $ok++
            } else {
                $failed += $perm
            }
        }
    }
}

# --- summary ---------------------------------------------------------------
Write-Host ""
Write-Host "-------------------------------------------------" -ForegroundColor DarkGray
if ($Revoke) {
    Write-Host "Runtime permissions revoked." -ForegroundColor Yellow
} else {
    Write-Host "Granted: $ok" -ForegroundColor Green
    if ($skipped) { Write-Host "Skipped (unsupported on API $apiLevel): $skipped" -ForegroundColor DarkGray }
    if ($failed) {
        Write-Host "Could not grant:" -ForegroundColor Yellow
        $failed | ForEach-Object { Write-Host "   $_" }
    }
}

Write-Host ""
Write-Host "Three permissions CANNOT be granted by any tool." -ForegroundColor Yellow
Write-Host "Android requires a human tap for each. Open Settings and enable:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. All files access   : Settings > Apps > See all apps > Stella"
Write-Host "                          > Permissions > Files and media > All the time"
Write-Host "  2. Display over apps  : same app page > Display over other apps = ON"
Write-Host "  3. Autopilot          : Settings > Accessibility > Installed services"
Write-Host "                          > Stella Autopilot = ON"
Write-Host ""
Write-Host "Screen control is asked for in-app each time it is used, by design." -ForegroundColor DarkGray