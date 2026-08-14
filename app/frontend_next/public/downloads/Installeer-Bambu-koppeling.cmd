@echo off
setlocal
title 3D Print Manager - Bambu Studio koppeling
set "SITE_URL=http://10.5.1.150:38502"
set "INSTALL_DIR=%LOCALAPPDATA%\3DPrintManager\BambuLauncher"

echo De koppeling met Bambu Studio wordt geinstalleerd...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing '%SITE_URL%/downloads/BambuLauncher.ps1' -OutFile '%INSTALL_DIR%\BambuLauncher.ps1'"
if errorlevel 1 goto error
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%\BambuLauncher.ps1" -Install -TrustedOrigin "%SITE_URL%"
if errorlevel 1 goto error

echo.
echo Installatie gereed. Druk op een toets om dit venster te sluiten.
pause >nul
exit /b 0

:error
echo.
echo Installatie mislukt. Controleer of %SITE_URL% bereikbaar is en probeer opnieuw.
pause
exit /b 1
