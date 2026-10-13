$ErrorActionPreference = 'Stop'
# Resumable fetch of the Gradle 8.7 distribution into the wrapper dists dir
# that gradlew.bat already started. Safe to re-run; picks up at .part size.
$dir  = "$env:USERPROFILE/.gradle/wrapper/dists/gradle-8.7-bin/bhs2wmbdwecv87pi65oeuq5iu"
$url  = 'https://services.gradle.org/distributions/gradle-8.7-bin.zip'
$part = Join-Path $dir 'gradle-8.7-bin.zip.part'
$dst  = Join-Path $dir 'gradle-8.7-bin.zip'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$have = if (Test-Path $part) { (Get-Item $part).Length } else { 0 }
$maxRetries = 40
for ($i = 0; $i -lt $maxRetries; $i++) {
  try {
    $req = [System.Net.HttpWebRequest]::Create($url)
    $req.Timeout = 25000; $req.ReadWriteTimeout = 25000
    if ($have -gt 0) { $req.AddRange($have) }
    $resp = $req.GetResponse()
    $total = $have + $resp.ContentLength
    $fs = [IO.File]::OpenWrite($part); $fs.Seek($have, 'Begin') | Out-Null
    $rs = $resp.GetResponseStream()
    $buf = New-Object byte[] 262144
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while (($n = $rs.Read($buf, 0, $buf.Length)) -gt 0) {
      $fs.Write($buf, 0, $n); $have += $n
      if ($sw.ElapsedMilliseconds -gt 2000) {
        "{0:o} have={1} total={2}" -f (Get-Date), $have, $total | Out-File "$dir/fetch_progress.txt"
        $sw.Restart()
      }
    }
    $fs.Close(); $rs.Close(); $resp.Close()
    if ($total -gt 0 -and $have -ge $total) {
      Move-Item $part $dst -Force
      "DONE bytes=$have" | Out-File "$dir/fetch_progress.txt"
      exit 0
    }
  } catch { Start-Sleep -Seconds 5 }
}
"DID-NOT-FINISH have=$have" | Out-File "$dir/fetch_progress.txt"
exit 1
