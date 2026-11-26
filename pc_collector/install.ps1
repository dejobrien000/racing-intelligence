# Racing Intelligence PC collector - installer (Windows 10/11, Windows PowerShell 5.1).
# Right-click this file > Run with PowerShell. It asks for Windows permission once (to create the scheduled tasks), asks for
# your GitHub token once (typed into this window only; never sent anywhere except GitHub), then tests everything.
# Re-running is safe: it updates the program and tasks and keeps the stored token (use -NewToken to replace it).
param([switch]$NewToken, [switch]$TestMode, [string]$InstallUser = '', [string]$InstallRoot = '')
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$Ver = '1.0.0'
$PyVer = '3.12.8'
function Say($m, $c = 'White') { Write-Host $m -ForegroundColor $c }
function Fail($m) { Say "`nPROBLEM: $m" 'Red'; if (-not $TestMode) { Read-Host 'Press Enter to close' }; exit 1 }

# 1. remember who is installing, then ask Windows for permission (task registration needs it)
if (-not $InstallUser) { $InstallUser = "$env:USERDOMAIN\$env:USERNAME" }
if (-not $InstallRoot) { $InstallRoot = Join-Path $env:LOCALAPPDATA 'RacingCollector' }
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Say 'Asking Windows for permission to set up the scheduled tasks...' 'Cyan'
    $a = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -InstallUser `"$InstallUser`" -InstallRoot `"$InstallRoot`""
    if ($NewToken) { $a += ' -NewToken' }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $a -Wait
    exit 0
}
Say "Racing Intelligence PC collector $Ver - installing for $InstallUser into $InstallRoot" 'Cyan'
$App = Join-Path $InstallRoot 'app'; $Py = Join-Path $InstallRoot 'python'; $Sec = Join-Path $InstallRoot 'secret'
foreach ($d in @($InstallRoot, $App, $Py, $Sec, (Join-Path $InstallRoot 'logs'), (Join-Path $InstallRoot 'state'), (Join-Path $InstallRoot 'data'))) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

# 2. program files
Copy-Item -Force (Join-Path $PSScriptRoot 'collector.py') (Join-Path $App 'collector.py')
Copy-Item -Force (Join-Path $PSScriptRoot 'uninstall.ps1') (Join-Path $InstallRoot 'uninstall.ps1')
Set-Content -Path (Join-Path $InstallRoot 'VERSION') -Value $Ver

# 3. a private copy of Python (does not touch any other Python on the PC)
$pyExe = Join-Path $Py 'python.exe'
if (-not (Test-Path $pyExe)) {
    Say "Downloading Python $PyVer (about 10 MB) from python.org..." 'Cyan'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
    $zip = Join-Path $env:TEMP "python-$PyVer-embed-$arch.zip"
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/$PyVer/python-$PyVer-embed-$arch.zip" -OutFile $zip
    Expand-Archive -Force -Path $zip -DestinationPath $Py
    Remove-Item $zip -Force
}
$sig = Get-AuthenticodeSignature $pyExe
if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Python Software Foundation') { Fail "python.exe is not signed by the Python Software Foundation ($($sig.Status)). Delete $Py and run again." }
Say "Python ready ($($sig.SignerCertificate.Subject -replace ',.*',''))." 'Green'

# 4. GitHub token: typed here, checked with GitHub, stored encrypted (Windows DPAPI) in a file only you and Windows can read
$tokFile = Join-Path $Sec 'github_token.bin'
Add-Type -AssemblyName System.Security
$entropy = [Text.Encoding]::ASCII.GetBytes('RacingIntelligence-PC-collector')
& icacls.exe $Sec /inheritance:r /grant:r "${InstallUser}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null   # you, Windows, administrators
if (-not $NewToken -and -not $TestMode -and (Test-Path $tokFile)) {   # a stored key that GitHub no longer accepts (expired or revoked) -> ask for a new one
    try {
        $old = [Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($tokFile), $entropy, [Security.Cryptography.DataProtectionScope]::LocalMachine))
        Invoke-RestMethod -Uri 'https://api.github.com/repos/dejobrien000/racing-intelligence' -Headers @{ Authorization = "Bearer $old"; 'User-Agent' = 'RacingCollector-installer' } | Out-Null
    } catch {
        $code = 0; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
        if ($code -in 401, 403, 404) { Say 'The GitHub key stored earlier no longer works (expired or removed). You will be asked for a new one.' 'Yellow'; $NewToken = $true }
        else { Say 'Could not reach GitHub to check the stored key; keeping it.' 'Yellow' }
    }
    $old = $null
}
if ($NewToken -or -not (Test-Path $tokFile)) {
    if ($TestMode) { $plain = $env:RC_TEST_TOKEN }
    else {
        Say "`nPaste your GitHub token below (Ctrl+V or right-click; it shows as *****) and press Enter." 'Yellow'
        $s = Read-Host -AsSecureString 'GitHub token'
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
    }
    $plain = $plain.Trim()
    if ($plain.Length -lt 20) { Fail 'That does not look like a GitHub token. Run the installer again and paste the whole token.' }
    if (-not $TestMode) {
        try { $r = Invoke-RestMethod -Uri 'https://api.github.com/repos/dejobrien000/racing-intelligence' -Headers @{ Authorization = "Bearer $plain"; 'User-Agent' = 'RacingCollector-installer' } }
        catch { Fail 'GitHub did not accept the token for repository racing-intelligence. Check it was created for that repository with Contents: Read and write.' }
    }
    $blob = [Security.Cryptography.ProtectedData]::Protect([Text.Encoding]::UTF8.GetBytes($plain), $entropy, [Security.Cryptography.DataProtectionScope]::LocalMachine)
    [IO.File]::WriteAllBytes($tokFile, $blob)
    $plain = $null; $s = $null; [GC]::Collect()
    Say 'Token stored (encrypted; readable only by your account and Windows).' 'Green'
} else { Say 'Using the token stored earlier (run with -NewToken to replace it).' 'Green' }

# 5. scheduled tasks: wake the PC, run late if the PC was off or asleep, retry on failure, never two copies at once
$folder = '\RacingIntelligence\'
$principal = New-ScheduledTaskPrincipal -UserId $InstallUser -LogonType S4U -RunLevel Limited
function Act($job) { New-ScheduledTaskAction -Execute $pyExe -Argument "-I `"$App\collector.py`" $job" -WorkingDirectory $InstallRoot }
function Sets($limit) { New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit $limit -MultipleInstances IgnoreNew }
function Rep($at, $every, $for) { $t = New-ScheduledTaskTrigger -Daily -At $at; $t.Repetition = (New-ScheduledTaskTrigger -Once -At $at -RepetitionInterval $every -RepetitionDuration $for).Repetition; $t }
$tStart = New-ScheduledTaskTrigger -AtStartup; $tStart.Delay = 'PT3M'          # wait a few minutes for the network
$tLogon = New-ScheduledTaskTrigger -AtLogOn -User $InstallUser; $tLogon.Delay = 'PT2M'
$tasks = @(
    @{ n = 'Morning racecards'; j = 'morning'; t = @(New-ScheduledTaskTrigger -Daily -At '07:30'); l = (New-TimeSpan -Hours 1) },
    @{ n = 'Form records'; j = 'form'; t = @(New-ScheduledTaskTrigger -Daily -At '07:40'); l = (New-TimeSpan -Hours 3) },
    @{ n = 'Evening results'; j = 'evening'; t = @(Rep '18:30' (New-TimeSpan -Minutes 30) (New-TimeSpan -Hours 8 -Minutes 31)); l = (New-TimeSpan -Minutes 25) },
    @{ n = 'Catch-up'; j = 'catchup'; t = @($tStart, $tLogon, (Rep '05:30' (New-TimeSpan -Hours 2) (New-TimeSpan -Hours 18))); l = (New-TimeSpan -Hours 3) },
    @{ n = 'Self-test'; j = 'selftest'; t = @(); l = (New-TimeSpan -Minutes 10) }
)
foreach ($k in $tasks) {
    $args_ = @{ TaskName = $k.n; TaskPath = $folder; Action = (Act $k.j); Settings = (Sets $k.l); Principal = $principal; Force = $true; Description = "Racing Intelligence PC collector $Ver ($($k.j))" }
    if ($k.t.Count) { $args_.Trigger = $k.t }
    Register-ScheduledTask @args_ | Out-Null
    Say "Task ready: $($k.n)" 'Green'
}
if ((Get-TimeZone).Id -ne 'E. Australia Standard Time') { Say "NOTE: this PC's time zone is $((Get-TimeZone).Id), not Brisbane. The tasks run at 07:30 / 07:40 / 18:30 PC time." 'Yellow' }

# 6. let scheduled tasks wake the PC when it is plugged in (Windows setting 'Allow wake timers')
& powercfg.exe /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null; & powercfg.exe /SETACTIVE SCHEME_CURRENT | Out-Null
Say 'Wake timers allowed while plugged in.' 'Green'

# 7. self-test, run the same way the real jobs run (as a scheduled task)
if ($TestMode) { Say 'Test mode: self-test task not started.' 'Yellow'; exit 0 }
$res = Join-Path $InstallRoot 'state\selftest.json'; Remove-Item -Force -ErrorAction SilentlyContinue $res
Say "`nRunning the self-test (reads TAB, uploads a test file to GitHub and reads it back)..." 'Cyan'
Start-ScheduledTask -TaskPath $folder -TaskName 'Self-test'
$deadline = (Get-Date).AddMinutes(4)
while (-not (Test-Path $res) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 3 }
if (-not (Test-Path $res)) { Fail "The self-test did not finish. Look at the newest file in $InstallRoot\logs and send it to Claude." }
$r = Get-Content $res -Raw | ConvertFrom-Json
if ($r.passed) {
    Say "`nALL DONE. Self-test passed. Today's TAB meetings seen: $($r.meetings_today -join ', ')." 'Green'
    Say 'The PC now collects racecards at 7:30am, form records at 7:40am and results from 6:30pm. Keep it plugged in; sleep is fine, shutting it down is not.' 'Green'
} else { Fail "Self-test failed: $($r.error). Send this message to Claude." }
Read-Host 'Press Enter to close'
