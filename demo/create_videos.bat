@echo off
cd /d "%~dp0\.."
echo =============================================
echo  ExcelProcessor — Generator Video Demo
echo =============================================
echo.
python demo/record_demos.py
echo.
pause
