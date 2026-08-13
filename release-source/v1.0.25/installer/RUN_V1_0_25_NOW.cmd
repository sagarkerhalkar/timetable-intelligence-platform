@echo off
setlocal
cd /d "%~dp0"
echo.
echo Timetable Intelligence Platform v1.0.25
echo Paged UX + Larger QR Library
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL_V1_0_25.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (
  echo v1.0.25 was NOT accepted. See the log printed above.
  echo If files had been applied, the installer attempted automatic rollback.
) else (
  echo v1.0.25 acceptance completed successfully.
)
echo.
pause
exit /b %RC%
