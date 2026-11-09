# =============================================================================
# Stella Cross-OS Permission Grant Script (Windows PowerShell)
# =============================================================================
# Automatically grants all permissions required for Stella's full operation
# on Windows. Runs without user confirmation where possible.
#
# Usage:
#   PowerShell -ExecutionPolicy Bypass -File scripts\grant_stella_permissions.ps1
# =============================================================================

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Verbose,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$VerbosePreference = "SilentlyContinue"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Status {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] [$Level] $Message" -ForegroundColor Cyan
}

function Test-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $pr = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $pr.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-Admin {
    if (-not (Test-Admin)) {
        Write-Status "ERROR: This script must run as Administrator to grant all permissions." -Level ERROR
        Write-Status "Right-click PowerShell and select 'Run as Administrator'." -Level ERROR
        exit 1
    }
    Write-Status "Running with Administrator privileges." -Level OK
}

function Test-Command {
    param([string]$Command)
    return (Get-Command $command -ErrorAction SilentlyContinue) -ne $null
}

function Set-RegistryValue {
    param([string]$Path, [string]$Name, [string]$Value, [string]$Type = "String")
    try {
        if (-not (Test-Path $Path)) {
            New-Item -Path $Path -Force | Out-Null
        }
        Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $Type -ErrorAction Stop
        return $true
    } catch {
        Write-Status "Failed to set registry $Path\$Name: $_" -Level ERROR
        return $false
    }
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Write-Status "========================================================================"
Write-Status " Stella Permission Grant Script (Windows)"
Write-Status "========================================================================"

# Ensure admin
Ensure-Admin

$granted = @()
$failed = @()

# --- 1. Filesystem permissions ---------------------------------------------
Write-Status "Granting filesystem permissions..."

$stellaDirs = @(
    "$env:LOCALAPPDATA\StellaAI",
    "$env:LOCALAPPDATA\StellaAI\config",
    "$env:LOCALAPPDATA\StellaAI\deliverables",
    "$env:LOCALAPPDATA\StellaAI\models",
    "$env:LOCALAPPDATA\StellaAI\audit",
)

foreach ($dir in $stellaDirs) {
    try {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        # Grant full control to everyone (broad access for dev)
        icacls $dir /grant Everyone:F /T /Q 2>$null | Out-Null
        Write-Status "Granted filesystem access: $dir" -Level OK
        $granted += "Filesystem: $dir"
    } catch {
        Write-Status "Failed to grant filesystem access: $dir - $_" -Level ERROR
        $failed += "Filesystem: $dir - $_"
    }
}

# --- 2. Registry keys ------------------------------------------------------
Write-Status "Granting registry access..."

$regKeys = @(
    "HKCU\Software\StellaAI",
    "HKCU\Software\StellaAI\Settings",
    "HKLM\Software\StellaAI",
)

foreach ($regKey in $regKeys) {
    if (Set-RegistryValue -Path $regKey -Name "Installed" -Value 1 -Type "DWord") {
        Write-Status "Granted registry access: $regKey" -Level OK
        $granted += "Registry: $regKey"
    }
}

# --- 3. Firewall rules -----------------------------------------------------
Write-Status "Configuring firewall rules..."

$fwRules = @(
    @{Name="Stella Connect"; LocalPort="8000"; Protocol="TCP"},
    @{Name="Stella Gateway"; LocalPort="8765"; Protocol="TCP"},
)

foreach ($rule in $fwRules) {
    try {
        $ruleName = $rule.Name
        $existing = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
        if (-not $existing) {
            New-NetFirewallRule -DisplayName $ruleName -Name $ruleName `
                -Direction Inbound -Protocol $rule.Protocol -LocalPort $rule.LocalPort `
                -Action Allow -Profile Any -Enabled:$true | Out-Null
        }
        Write-Status "Firewall rule enabled: $ruleName (port $($rule.LocalPort))" -Level OK
        $granted += "Firewall: $ruleName ($($rule.LocalPort))"
    } catch {
        Write-Status "Failed to create firewall rule: $ruleName - $_" -Level ERROR
        $failed += "Firewall: $ruleName - $_"
    }
}

# --- 4. Execution policy ---------------------------------------------------
Write-Status "Configuring PowerShell execution policy..."

try {
    $currentPolicy = Get-ExecutionPolicy -Scope CurrentUser -ErrorAction SilentlyContinue
    if ($currentPolicy -ne "RemoteSigned" -and $currentPolicy -ne "Unrestricted") {
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force | Out-Null
        Write-Status "PowerShell execution policy set to RemoteSigned (CurrentUser)" -Level OK
        $granted += "PowerShell execution policy: RemoteSigned"
    } else {
        Write-Status "PowerShell execution policy already set to $currentPolicy" -Level OK
    }
} catch {
    Write-Status "Failed to set execution policy: $_" -Level ERROR
    $failed += "PowerShell execution policy: $_"
}

# --- 5. Developer mode (optional, Windows 10+) ---------------------------
Write-Status "Checking developer mode..."

try {
    $devKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
    if (-not (Test-Path $devKey)) {
        New-Item -Path $devKey -Force | Out-Null
    }
    Set-ItemProperty -Path $devKey -Name "AllowDevelopmentWithoutDevLicense" -Value 1 -Type DWord -Force | Out-Null
    Write-Status "Developer mode enabled" -Level OK
    $granted += "Developer mode: enabled"
} catch {
    Write-Status "Could not enable developer mode: $_" -Level WARNING
}

# --- 6. Summary ------------------------------------------------------------
Write-Status ""
Write-Status "========================================================================"
Write-Status " Permission Grant Summary"
Write-Status "========================================================================"
Write-Status "Granted: $($granted.Count) item(s)"
foreach ($g in $granted) {
    Write-Status "  [+] $g" -ForegroundColor Green
}
if ($failed.Count -gt 0) {
    Write-Status "Failed: $($failed.Count) item(s)"
    foreach ($f in $failed) {
        Write-Status "  [-] $f" -ForegroundColor Red
    }
}
Write-Status ""
Write-Status "Stella permissions have been granted where possible."
Write-Status "Review any failures above and resolve manually if needed."
Write-Status "========================================================================"

if ($failed.Count -gt 0) {
    exit 1
}
