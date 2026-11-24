# Punting Form Starter API: probe and resumable history download. Runs on Damo's PC only.
#
# CREDENTIALS
#   -SetKey asks for the API key once (typing is hidden) and stores it ENCRYPTED with Windows DPAPI in
#   %LOCALAPPDATA%\racing_pf\pf_key.dpapi. Only the same Windows user on the same PC can decrypt it.
#   The key is never printed, never written to any output or log, and is removed from any error text.
#   That folder is not shared with Claude (Claude only sees Downloads).
#
# NETWORK
#   Only https://api.puntingform.com.au/v2/form/meetingslist, /results and (probe only) /fields.
#   The API takes the key as an apiKey= query parameter; nothing else is sent.
#
# FILES WRITTEN (all in Downloads\racing_pf)
#   probe\*.json                raw probe responses + probe_summary.txt (status codes, sizes, headers)
#   pf_meetings_YYYY-MM.jsonl   one line per date: the meetings list
#   pf_results_YYYY-MM.jsonl    one line per meeting: the results
#   pf_log.txt                  progress log (no key)
#
# RESUMING: dates already listed and meetings already saved are skipped, so an interrupted run
# carries on where it stopped and never re-downloads completed meetings.
#
# USAGE (from PowerShell in Downloads\racing_pf):
#   .\pf_backfill.ps1 -SetKey      store the key (once)
#   .\pf_backfill.ps1 -Probe       small multi-year test, ~40 requests
#   .\pf_backfill.ps1              full download, 2022-10-01 to yesterday, NSW/VIC/ACT/QLD

param(
  [switch]$SetKey,
  [switch]$Probe,
  [string]$OutDir  = "$env:USERPROFILE\Downloads\racing_pf",
  [string]$From    = "2022-10-01",
  [string]$To      = "",
  [string[]]$States = @("NSW", "VIC", "ACT", "QLD"),
  [double]$PauseSeconds = 0.8
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$KeyDir  = Join-Path $env:LOCALAPPDATA "racing_pf"
$KeyFile = Join-Path $KeyDir "pf_key.dpapi"

if ($SetKey) {
  New-Item -ItemType Directory -Force -Path $KeyDir | Out-Null
  $sec = Read-Host -Prompt "Paste your Punting Form API key, then press Enter (it won't show)" -AsSecureString
  ConvertFrom-SecureString -SecureString $sec | Set-Content -Path $KeyFile -Encoding ASCII
  Write-Host "Key saved (encrypted for your Windows account only)." -ForegroundColor Green
  exit 0
}
if (-not (Test-Path $KeyFile)) { Write-Host "No key stored yet. Run:  .\pf_backfill.ps1 -SetKey" -ForegroundColor Red; exit 1 }
$sec = Get-Content $KeyFile | ConvertTo-SecureString
$key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
if ($key.Length -lt 8) { Write-Host "The stored key looks empty. Run -SetKey again." -ForegroundColor Red; exit 1 }
if (-not $To) { $To = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd") }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$base = "https://api.puntingform.com.au/v2/form"
$logFile = Join-Path $OutDir "pf_log.txt"
function Safe([string]$t) { if ($t) { return $t.Replace($key, "***") } else { return $t } }
function Log($msg) { $line = Safe "$(Get-Date -Format s) $msg"; Add-Content -Encoding UTF8 -Path $logFile -Value $line; Write-Host $line }

function Get-PF([string]$path, [string]$query) {
  $url = "$base/$path`?$query&apiKey=$key"
  for ($i = 1; $i -le 3; $i++) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -Headers @{ accept = "application/json" } -TimeoutSec 90
      $h = ($r.Headers.Keys | Where-Object { $_ -match 'rate|limit|quota|retry|remaining' } | ForEach-Object { "$_=$($r.Headers[$_])" }) -join "; "
      return @{ ok = $true; status = [int]$r.StatusCode; body = ($r.Content -replace "`r?`n", " "); headers = $h }
    } catch {
      $code = $null; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
      if ($code -in @(400, 401, 403, 404)) { return @{ ok = $false; status = $code; body = $null; headers = "" } }
      if ($code -eq 429) { Start-Sleep -Seconds 60 } else { Start-Sleep -Seconds (5 * $i) }
      if ($i -eq 3) { return @{ ok = $false; status = $code; body = $null; headers = "" } }
    }
  }
}

function Find-Meetings($obj) {
  $found = @()
  if ($obj -is [System.Array]) { foreach ($o in $obj) { $found += Find-Meetings $o } }
  elseif ($obj -is [System.Management.Automation.PSCustomObject]) {
    $names = $obj.PSObject.Properties.Name
    if ($names -contains "meetingId" -or $names -contains "MeetingId") { $found += $obj }
    else { foreach ($p in $obj.PSObject.Properties) { $found += Find-Meetings $p.Value } }
  }
  return $found
}
function Id-Of($m) { if ($m.meetingId) { return $m.meetingId } else { return $m.MeetingId } }
function State-Of($m) { foreach ($c in @($m.track.state, $m.Track.State, $m.state, $m.State)) { if ($c) { return [string]$c } }; return "" }
function Track-Of($m) { foreach ($c in @($m.track.name, $m.Track.Name, $m.trackName, $m.TrackName, $m.name)) { if ($c) { return [string]$c } }; return "" }

if ($Probe) {
  $pd = Join-Path $OutDir "probe"; New-Item -ItemType Directory -Force -Path $pd | Out-Null
  $summary = Join-Path $pd "probe_summary.txt"; Set-Content -Path $summary -Value "date|endpoint|meetingId|track|state|status|bytes|rate_headers" -Encoding UTF8
  # Metro NSW and Victorian days across years (plus two older days to test depth).
  $dates = @("2026-10-03", "2025-03-08", "2024-10-19", "2023-11-07", "2023-04-08", "2015-11-03", "2006-11-07")
  $wanted = @("Randwick", "Royal Randwick", "Rosehill", "Rosehill Gardens", "Flemington", "Caulfield", "Moonee Valley")
  foreach ($d in $dates) {
    $ml = Get-PF "meetingslist" "meetingDate=$d"
    Add-Content -Path $summary -Encoding UTF8 -Value "$d|meetingslist|||$($ml.status)|$(if ($ml.body) { $ml.body.Length } else { 0 })|$($ml.headers)"
    if ($ml.status -in @(401, 403)) { Log "Probe stopped: the API refused the key (status $($ml.status)). The subscription may not include API access yet."; exit 1 }
    if (-not $ml.ok) { Log "probe $d meetingslist failed (status $($ml.status))"; continue }
    Set-Content -Encoding UTF8 -Path (Join-Path $pd "meetingslist_$d.json") -Value $ml.body
    $meet = Find-Meetings ($ml.body | ConvertFrom-Json)
    $pick = @($meet | Where-Object { (Track-Of $_) -in $wanted } | Select-Object -First 2)
    if ($pick.Count -eq 0) { $pick = @($meet | Select-Object -First 1) }
    foreach ($m in $pick) {
      $id = Id-Of $m
      foreach ($ep in @("results", "fields")) {
        $r = Get-PF $ep "meetingId=$id&raceNumber=0"
        Add-Content -Path $summary -Encoding UTF8 -Value "$d|$ep|$id|$(Track-Of $m)|$(State-Of $m)|$($r.status)|$(if ($r.body) { $r.body.Length } else { 0 })|$($r.headers)"
        if ($r.ok) { Set-Content -Encoding UTF8 -Path (Join-Path $pd "${ep}_${d}_$id.json") -Value $r.body }
        Start-Sleep -Seconds $PauseSeconds
      }
    }
    Log "probe $d : $($meet.Count) meetings listed"
    Start-Sleep -Seconds $PauseSeconds
  }
  Log "Probe finished. Tell Claude it's done."
  exit 0
}

# Full, resumable download
$doneDates = @{}; $doneMeetings = @{}
Get-ChildItem $OutDir -Filter "pf_meetings_*.jsonl" -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_.FullName | ForEach-Object { if ($_ -match '"date":"(\d{4}-\d{2}-\d{2})"') { $doneDates[$Matches[1]] = $true } } }
Get-ChildItem $OutDir -Filter "pf_results_*.jsonl" -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_.FullName | ForEach-Object { if ($_ -match '"meetingId":(\d+)') { $doneMeetings[$Matches[1]] = $true } } }
$day = [datetime]::ParseExact($From, "yyyy-MM-dd", $null); $end = [datetime]::ParseExact($To, "yyyy-MM-dd", $null)
Log "full run $From to $To, states $($States -join ','), $($doneDates.Count) dates and $($doneMeetings.Count) meetings already saved"
while ($day -le $end) {
  $d = $day.ToString("yyyy-MM-dd"); $month = $day.ToString("yyyy-MM")
  if (-not $doneDates.ContainsKey($d)) {
    $ml = Get-PF "meetingslist" "meetingDate=$d"
    if ($ml.status -in @(401, 403)) { Log "Stopped: the API refused the key (status $($ml.status))."; exit 1 }
    if ($ml.ok) {
      $meet = Find-Meetings ($ml.body | ConvertFrom-Json); $n = 0; $skip = 0; $fail = 0
      foreach ($m in $meet) {
        if ((State-Of $m) -notin $States) { continue }
        $id = [string](Id-Of $m)
        if ($doneMeetings.ContainsKey($id)) { $skip++; continue }
        $r = Get-PF "results" "meetingId=$id&raceNumber=0"
        if ($r.ok) {
          Add-Content -Encoding UTF8 -Path (Join-Path $OutDir "pf_results_$month.jsonl") -Value ('{"date":"' + $d + '","meetingId":' + $id + ',"retrieved_utc":"' + (Get-Date).ToUniversalTime().ToString("s") + 'Z","body":' + $r.body + '}')
          $doneMeetings[$id] = $true; $n++
        } else { $fail++; Log "results failed for meeting $id on $d (status $($r.status))" }
        Start-Sleep -Seconds $PauseSeconds
      }
      if ($fail -eq 0) {
        Add-Content -Encoding UTF8 -Path (Join-Path $OutDir "pf_meetings_$month.jsonl") -Value ('{"date":"' + $d + '","retrieved_utc":"' + (Get-Date).ToUniversalTime().ToString("s") + 'Z","body":' + $ml.body + '}')
      }
      Log "$d : $($meet.Count) listed, $n saved, $skip already had, $fail failed"
    } else { Log "$d : meetings list failed (status $($ml.status)), will retry next run" }
    Start-Sleep -Seconds $PauseSeconds
  }
  $day = $day.AddDays(1)
}
Log "Finished. Tell Claude it's done."
