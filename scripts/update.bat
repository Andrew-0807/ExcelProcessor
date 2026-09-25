@echo off
REM Copy this file next to ExcelProcessor.exe on the client PC.
REM Pulls the latest loose source from the dev PC's read-only share and restarts.
REM Set SRC to the dev PC's Radmin VPN IP.
set SRC=\\26.0.0.1\MomAppDist

echo Closing Excel Processor...
taskkill /IM ExcelProcessor.exe /F >nul 2>&1

echo Updating from %SRC% ...
robocopy "%SRC%\app"     "%~dp0app"     /MIR /XD __pycache__ /NP /NFL /NDL
if errorlevel 8 goto fail
robocopy "%SRC%\scripts" "%~dp0scripts" /MIR /XD __pycache__ /NP /NFL /NDL
if errorlevel 8 goto fail

echo Done. Starting...
start "" "%~dp0ExcelProcessor.exe"
exit /b 0

:fail
echo.
echo UPDATE FAILED - could not reach %SRC%. Is the Radmin VPN connected?
echo The old version still works: start ExcelProcessor.exe normally.
pause
exit /b 1
