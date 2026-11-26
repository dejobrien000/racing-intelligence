@echo off
rem Double-click to remove the Racing Intelligence PC collector (scheduled tasks and its folder, stored key included).
if not exist "%LOCALAPPDATA%\RacingCollector\uninstall.ps1" (echo The collector is not installed. & pause & exit /b 0)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\RacingCollector\uninstall.ps1" -DeleteFiles
