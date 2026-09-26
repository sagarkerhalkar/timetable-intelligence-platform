@echo off
setlocal
cd /d "%~dp0"
title Restore Google Sheets and Today Timetable
echo.
echo GOOGLE SHEET + TODAY TIMETABLE RECOVERY
echo.
echo This does NOT install v1.0.25.
echo This does NOT delete QR codes.
echo It backs up the populated database, then uses the app's own sync API.
echo.
set "PY="
if exist "D:\timetable-intelligence-platform\services\api\.venv\Scripts\python.exe" set "PY=D:\timetable-intelligence-platform\services\api\.venv\Scripts\python.exe"
if not defined PY if exist "D:\timetable-intelligence-platform\.venv\Scripts\python.exe" set "PY=D:\timetable-intelligence-platform\.venv\Scripts\python.exe"
if not defined PY set "PY=python"
"%PY%" "%~dp0RESTORE_GOOGLE_SHEETS_TODAY.py"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo SUCCESS - reload the Timetable page.
) else (
  echo Recovery returned exit code %RC%.
  echo The Desktop report contains the exact source status/error.
)
echo.
pause
exit /b %RC%
