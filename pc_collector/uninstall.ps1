# Removes the Racing Intelligence PC collector's scheduled tasks. Add -DeleteFiles to also delete its folder (token included).
param([switch]$DeleteFiles, [switch]$Quiet)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $(if ($DeleteFiles) {'-DeleteFiles'}) $(if ($Quiet) {'-Quiet'})" -Wait; exit 0 }
Get-ScheduledTask -TaskPath '\RacingIntelligence\' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
Write-Host 'Scheduled tasks removed.' -ForegroundColor Green
if ($DeleteFiles) { Remove-Item -Recurse -Force (Split-Path -Parent $PSCommandPath); Write-Host 'Collector folder deleted.' -ForegroundColor Green }
if (-not $Quiet) { Read-Host 'Press Enter to close' }
