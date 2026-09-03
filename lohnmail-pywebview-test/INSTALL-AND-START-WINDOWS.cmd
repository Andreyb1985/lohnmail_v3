@echo off
setlocal
set "ROOT_DIR=%~dp0"
if not exist "%ROOT_DIR%App\LohnMail.exe" if not exist "%ROOT_DIR%App\main.py" set "ROOT_DIR=%~dp0..\"
set "APP_DIR=%ROOT_DIR%App"
set "PYTHON_EXE=%APP_DIR%\.venv\Scripts\python.exe"
cd /d "%ROOT_DIR%"

if exist "%ROOT_DIR%LohnMail.exe" (
    "%ROOT_DIR%LohnMail.exe"
    if errorlevel 1 goto :error
    exit /b 0
)

if exist "%APP_DIR%\LohnMail.exe" (
    "%APP_DIR%\LohnMail.exe"
    if errorlevel 1 goto :error
    exit /b 0
)

if not exist "%APP_DIR%\main.py" (
    echo Der LohnMail-App-Ordner wurde nicht gefunden.
    goto :error
)

where py >nul 2>nul
if errorlevel 1 (
    echo Python 3 wurde nicht gefunden.
    echo Bitte Python 3.12 oder 3.13 von https://www.python.org/downloads/windows/ installieren.
    echo Bei der Installation "Add python.exe to PATH" aktivieren.
    goto :error
)

if not exist "%PYTHON_EXE%" (
    py -m venv "%APP_DIR%\.venv"
    if errorlevel 1 goto :error
)

if not exist "%APP_DIR%\.venv\.lohnmail-requirements-2.0.3" (
    "%PYTHON_EXE%" -m pip install -r "%APP_DIR%\requirements-windows.txt"
    if errorlevel 1 goto :error
    > "%APP_DIR%\.venv\.lohnmail-requirements-2.0.3" echo 2.0.3
)

"%PYTHON_EXE%" "%APP_DIR%\main.py"
if errorlevel 1 goto :error
exit /b 0

:error
set "EXIT_CODE=%errorlevel%"
if "%EXIT_CODE%"=="0" set "EXIT_CODE=1"
echo.
echo LohnMail konnte nicht gestartet werden. Fehlercode: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
