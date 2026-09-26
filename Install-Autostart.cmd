@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Autostart.ps1"
if errorlevel 1 echo Something went wrong.
echo To remove autostart, run Uninstall-Autostart.cmd.
pause
