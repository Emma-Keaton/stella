param(
    [string]$Log = "build_exe_public.log",
    [string]$Done = "build_exe_public.done",
    [int]$TimeoutMin = 40
)

$Root = "E:\Projects\stella"
$LogPath = Join-Path $Root $Log
$DonePath = Join-Path $Root $Done

if (Test-Path $DonePath) { Remove-Item $DonePath -Force }

$start = Get-Date
while (((Get-Date) - $start).TotalMinutes -lt $TimeoutMin) {
    if (Test-Path $LogPath) {
        $tail = Get-Content $LogPath -Tail 4 -ErrorAction SilentlyContinue
        if ($tail -match "Portable zip|BUILD|Traceback|Error") {
            "$(Get-Date -Format 'HH:mm:ss') $($tail -join ' | ')" | Out-File $DonePath -Encoding UTF8
            exit 0
        }
    }
    Start-Sleep -Seconds 30
}
"$(Get-Date -Format 'HH:mm:ss') TIMEOUT after ${TimeoutMin} min" | Out-File $DonePath -Encoding UTF8
exit 1
