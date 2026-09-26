@echo off
setlocal
cd /d "%~dp0"
if not exist data mkdir data
echo.
echo Jarvis - connect Spotify and YouTube. Values are saved only in the data folder on this PC.
echo Press Enter to skip a question.
echo.
set /p SP="Spotify Client ID: "
if not "%SP%"=="" powershell -NoProfile -Command "@{client_id=$env:SP} | ConvertTo-Json | Set-Content -Encoding UTF8 data\spotify.json" & echo Spotify saved.
set /p GI="Google (YouTube) Client ID: "
set /p GS="Google (YouTube) Client secret: "
if not "%GI%"=="" powershell -NoProfile -Command "@{client_id=$env:GI; client_secret=$env:GS} | ConvertTo-Json | Set-Content -Encoding UTF8 data\youtube.json" & echo YouTube saved.
echo.
echo Done. Restart Jarvis, then say: connect spotify  /  connect youtube
pause
