param(
    [int]$TimeoutMin = 45
)

$Root = "E:\Projects\stella"
$targets = @(
    @{ Log = "build_exe_public.log"; Marker = "Portable zip"; Name = "exe-public" },
    @{ Log = "build_apk_k2.log";     Marker = "BUILD SUCCESSFUL"; Name = "apk-k2" }
)
$DonePath = Join-Path $Root "build_all.done"
if (Test-Path $DonePath) { Remove-Item $DonePath -Force }

$state = @{}
foreach ($t in $targets) { $state[$t.Name] = $false }

$start = Get-Date
while (((Get-Date) - $start).TotalMinutes -lt $TimeoutMin) {
    foreach ($t in $targets) {
        if ($state[$t.Name]) { continue }
        $path = Join-Path $Root $t.Log
        if (Test-Path $path) {
            $tail = Get-Content $path -Tail 6 -ErrorAction SilentlyContinue
            if ($tail -match [regex]::Escape($t.Marker)) {
                $state[$t.Name] = $true
                "$(Get-Date -Format 'HH:mm:ss') $($t.Name): DONE" | Out-File $DonePath -Append -Encoding UTF8
            } elseif ($tail -match "Traceback|FAILED|CalledProcessError") {
                $state[$t.Name] = $true
                "$(Get-Date -Format 'HH:mm:ss') $($t.Name): FAILED" | Out-File $DonePath -Append -Encoding UTF8
            }
        }
    }
    if (($state.Values | Where-Object { -not $_ }).Count -eq 0) {
        "$(Get-Date -Format 'HH:mm:ss') ALL DONE" | Out-File $DonePath -Append -Encoding UTF8
        exit 0
    }
    Start-Sleep -Seconds 20
}
"$(Get-Date -Format 'HH:mm:ss') TIMEOUT; state=$($state | ConvertTo-Json -Compress)" | Out-File $DonePath -Append -Encoding UTF8
exit 1

