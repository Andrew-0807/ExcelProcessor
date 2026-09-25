@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo Starting Excel Processor...
echo ============================================================

REM Find Python executable (prioritize environment with dependencies)
set "PY_EXE="
if exist "E:\Apps\scoop\apps\python\current\python.exe" (
    set "PY_EXE=E:\Apps\scoop\apps\python\current\python.exe"
) else (
    where python3 >nul 2>&1
    if not errorlevel 1 (
        set "PY_EXE=python3"
    ) else (
        where py >nul 2>&1
        if not errorlevel 1 (
            set "PY_EXE=py -3"
        ) else (
            where python >nul 2>&1
            if not errorlevel 1 (
                set "PY_EXE=python"
            )
        )
    )
)

if "%PY_EXE%"=="" (
    echo [ERROR] Python was not found on PATH.
    pause
    exit /b 1
)

echo Python launcher: %PY_EXE%
echo Web Interface:   http://127.0.0.1:5000
echo.

%PY_EXE% bootstrap.py
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error.
    pause
)
