# Stella Android permission grant/revoke PowerShell wrapper
param(
    [ValidateSet("grant","revoke")]
    [string]$Action = "grant",
    [string]$Permission = ""
)

$PACKAGE = "com.stella.connect"
$PERMS = @(
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.FOREGROUND_SERVICE",
    "android.permission.FOREGROUND_SERVICE_MICROPHONE",
    "android.permission.FOREGROUND_SERVICE_CAMERA",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.MANAGE_EXTERNAL_STORAGE",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.USE_FULL_SCREEN_INTENT"
)

function Test-Adb {
    if (-not (Get-Command adb -ErrorAction SilentlyContinue)) { Write-Error "adb not found"; exit 1 }
    $dev = adb devices | Select-String "device$"
    if (-not $dev) { Write-Error "No device connected"; exit 1 }
}

function Grant-Perm { param($p); Write-Host "Granting $p"; adb shell pm grant $PACKAGE $p | Out-Null; Write-Host "Done $p" }
function Revoke-Perm { param($p); Write-Host "Revoking $p"; adb shell pm revoke $PACKAGE $p | Out-Null; Write-Host "Done $p" }

Test-Adb

if ($Permission) {
    if ($Action -eq "grant") { Grant-Perm $Permission } else { Revoke-Perm $Permission }
} else {
    foreach ($p in $PERMS) {
        if ($Action -eq "grant") { Grant-Perm $p } else { Revoke-Perm $p }
    }
}
Write-Host "Completed"
