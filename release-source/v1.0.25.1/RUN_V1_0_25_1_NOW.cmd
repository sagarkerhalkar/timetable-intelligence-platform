@echo off
setlocal
cd /d "%~dp0"
echo.
echo Timetable Intelligence Platform v1.0.25.1
echo PowerShell Parser Fix + Paged UX + Larger QR Library
echo.
echo [1/2] Running parser safety precheck before any install action...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0PRECHECK_V1_0_25_1.ps1"
set PRECHECK_RC=%ERRORLEVEL%
if not "%PRECHECK_RC%"=="0" (
  echo.
  echo v1.0.25.1 PRECHECK FAILED. Nothing was installed or changed.
  echo Send the error shown above to ChatGPT.
  echo.
  pause
  exit /b %PRECHECK_RC%
)
echo.
echo [2/2] Starting protected acceptance installer...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL_V1_0_25_1.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (
  echo v1.0.25.1 was NOT accepted. See the log printed above.
  echo If files had been applied, the installer attempted automatic rollback.
) else (
  echo v1.0.25.1 acceptance completed successfully.
)
echo.
pause
exit /b %RC%
