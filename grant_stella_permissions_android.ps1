# Stella Android Permission Grant Script (PowerShell)
# Grants/revokes Android app permissions via ADB
# Supports per-permission grant/revoke and bulk operations for all Stella permissions.
#
# Usage:
#   .\grant_stella_permissions_android.ps1 -Action grant
#   .\grant_stella_permissions_android.ps1 -Action revoke
#   .\grant_stella_permissions_android.ps1 -Action grant -Permission android.permission.CAMERA
#
# Make sure ADB is in PATH and device is connected.

param(
    [ValidateSet('grant','revoke')]
    [string]$Action = 'grant',
    
    [string]$Permission = '',
    
    [string]$Package = 'com.stella.connect'
)

# Stella required permissions
$StellaPermissions = @(
    'android.permission.CAMERA',
    'android.permission.RECORD_AUDIO',
    'android.permission.ACCESS_FINE_LOCATION',
    'android.permission.ACCESS_COARSE_LOCATION',
    'android.permission.POST_NOTIFICATIONS',
    'android.permission.ACCESS_BACKGROUND_LOCATION',
    'android.permission.FOREGROUND_SERVICE',
    'android.permission.FOREGROUND_SERVICE_CAMERA',
    'android.permission.FOREGROUND_SERVICE_MICROPHONE',
    'android.permission.WRITE_EXTERNAL_STORAGE',
    'android.permission.READ_EXTERNAL_STORAGE',
    'android.permission.MANAGE_EXTERNAL_STORAGE',
    'android.permission.SYSTEM_ALERT_WINDOW',
    'android.permission.BIND_ACCESSIBILITY_SERVICE',
    'android.permission.USE_FULL_SCREEN_INTENT'
)

function Test-AdbDevice {
    $devices = adb devices | Select-String 'device$'
    if (-not $devices) {
        Write-Error "No ADB device connected. Connect device and enable USB debugging."
        exit 1
    }
    Write-Host "ADB device detected."
}

function Grant-Permission {
    param($Perm)
    Write-Host "Granting $Perm..."
    $out = adb shell pm grant $Package $Perm 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Granted: $Perm" -ForegroundColor Green
    } else {
        Write-Warning "  Could not grant $Perm (may require user approval): $out"
    }
}

function Revoke-Permission {
    param($Perm)
    Write-Host "Revoking $Perm..."
    $out = adb shell pm revoke $Package $Perm 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Revoked: $Perm" -ForegroundColor Yellow
    } else {
        Write-Warning "  Could not revoke $Perm: $out"
    }
}

Test-AdbDevice

if ($Permission) {
    if ($Action -eq 'grant') {
        Grant-Permission $Permission
    } else {
        Revoke-Permission $Permission
    }
} else {
    foreach ($perm in $StellaPermissions) {
        if ($Action -eq 'grant') {
            Grant-Permission $perm
        } else {
            Revoke-Permission $perm
        }
    }
}

Write-Host "Done."
