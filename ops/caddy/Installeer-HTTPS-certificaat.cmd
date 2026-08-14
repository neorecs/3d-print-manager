@echo off
setlocal
title 3D Print Manager - HTTPS certificaat
set "CERT_URL=http://10.5.1.150:38502/local-ca.crt"
set "CERT_FILE=%TEMP%\3d-print-manager-local-ca.crt"

echo Het lokale beveiligingscertificaat wordt geinstalleerd voor jouw Windows-account.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing '%CERT_URL%' -OutFile '%CERT_FILE%'"
if errorlevel 1 goto error

certutil.exe -user -addstore -f Root "%CERT_FILE%"
if errorlevel 1 goto error

del /q "%CERT_FILE%" >nul 2>&1
echo.
echo Installatie gereed. De beveiligde 3D Print Manager wordt geopend.
start "" "https://10.5.1.150:38503/"
timeout /t 3 >nul
exit /b 0

:error
echo.
echo Installatie mislukt. Controleer of de NAS bereikbaar is en probeer opnieuw.
pause
exit /b 1
