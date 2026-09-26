@echo off
setlocal
cd /d "%~dp0"
title Timetable Core DB Recovery - Preserve QR

echo.
echo TIMETABLE CORE / GOOGLE SHEET RECOVERY - PRESERVE QR
echo This does NOT install a QR/UI release.
echo Port 3457 is protected and will not be touched.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RECOVER_TIMETABLE_CORE_PRESERVE_QR.ps1"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo SUCCESS - Timetable core DB path restored, QR preserved, Sheet sync checked.
) else (
  echo RECOVERY FAILED with exit code %RC%.
  echo Do not install another release. Upload the Desktop recovery report.
)
echo.
pause
exit /b %RC%
