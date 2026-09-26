@echo off
setlocal
cd /d "%~dp0"
title NextToppers QR Branding and Performance
echo.
echo NEXTTOPPERS QR - BRANDING + PRODUCTION WEB RUNTIME
echo This does not modify the production database.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0APPLY_NEXTTOPPERS_QR_BRANDING_PERFORMANCE.ps1"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo SUCCESS - open https://nexttoppers.sagarkerhalkar.com
) else (
  echo FAILED - read the Desktop NEXTTOPPERS_QR log.
)
echo.
pause
exit /b %RC%
