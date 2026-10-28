<#
    .SYNOPSIS
        Watch one or more Stella build logs until they finish (or fail).

    .DESCRIPTION
        Merged from the former watch_all.ps1, watch_k2exe.ps1 (these two
        were byte-identical), watch_exe_public.ps1 and watch_k2_apk.ps1.
        Each target is a log file plus a success marker; the watcher polls
        the tail of each log, writes a .done marker file, and exits 0 when
        every watched target succeeds, 1 on timeout or failure.

    .PARAMETER Targets
        all         - exe-public + apk-k2 (default; old watch_all/watch_k2exe)
        exe-public  - portable zip build only (old watch_exe_public)
        apk-k2      - the k2 APK build only (old watch_k2_apk)

    .EXAMPLE
        .\scripts\watch_build.ps1
        .\scripts\watch_build.ps1 -Targets apk-k2 -TimeoutMin 25
#>
param(
    [ValidateSet('all', 'exe-public', 'apk-k2')]
    [string]$Targets = 'all',
    [int]$TimeoutMin = 45
)

$Root = "E:\Projects\stella"

$catalog = @{
    'exe-public' = @{ Log = 'build_exe_public.log'; Marker = 'Portable zip';     Name = 'exe-public'; Done = 'build_exe_public.done' }
    'apk-k2'     = @{ Log = 'build_apk_k2.log';     Marker = 'BUILD SUCCESSFUL'; Name = 'apk-k2';     Done = 'build_apk_k2.done' }
}

$selected = switch ($Targets) {
    'all'        { @($catalog['exe-public'], $catalog['apk-k2']) }
    'exe-public' { @($catalog['exe-public']) }
    'apk-k2'     { @($catalog['apk-k2']) }
}

# Shared done-file for the 'all' view, kept for anything polling build_all.done.
$AllDonePath = Join-Path $Root 'build_all.done'
if ($Targets -eq 'all' -and (Test-Path $AllDonePath)) { Remove-Item $AllDonePath -Force }

$state = @{}
foreach ($t in $selected) {
    $state[$t.Name] = $false
    $dp = Join-Path $Root $t.Done
    if (Test-Path $dp) { Remove-Item $dp -Force }
}

$start = Get-Date
while (((Get-Date) - $start).TotalMinutes -lt $TimeoutMin) {
    foreach ($t in $selected) {
        if ($state[$t.Name]) { continue }
        $path = Join-Path $Root $t.Log
        if (-not (Test-Path $path)) { continue }
        $tail = Get-Content $path -Tail 6 -ErrorAction SilentlyContinue
        $msg = $null
        if ($tail -match [regex]::Escape($t.Marker)) {
            $state[$t.Name] = $true
            $msg = "$($t.Name): DONE"
        } elseif ($tail -match 'Traceback|FAILED|CalledProcessError|BUILD FAILED') {
            $state[$t.Name] = $true
            $msg = "$($t.Name): FAILED"
        }
        if ($msg) {
            $line = "$(Get-Date -Format 'HH:mm:ss') $msg"
            $line | Out-File (Join-Path $Root $t.Done) -Encoding UTF8
            if ($Targets -eq 'all') { $line | Out-File $AllDonePath -Append -Encoding UTF8 }
        }
    }
    if (($state.Values | Where-Object { -not $_ }).Count -eq 0) {
        $line = "$(Get-Date -Format 'HH:mm:ss') ALL DONE"
        if ($Targets -eq 'all') { $line | Out-File $AllDonePath -Append -Encoding UTF8 }
        exit 0
    }
    Start-Sleep -Seconds 20
}
$line = "$(Get-Date -Format 'HH:mm:ss') TIMEOUT; state=$($state | ConvertTo-Json -Compress)"
if ($Targets -eq 'all') { $line | Out-File $AllDonePath -Append -Encoding UTF8 }
exit 1