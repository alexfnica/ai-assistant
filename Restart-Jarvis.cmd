@echo off
rem Stops any old JARVIS server (python + local model) so the new code really starts, then launches HOLO.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -like 'python*' -and $_.CommandLine -like '*jarvis*') -or $_.Name -eq 'llama-server.exe' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 >nul
call "%~dp0Start-Jarvis-HOLO.cmd"
