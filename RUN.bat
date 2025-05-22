@echo off
REM ========================================
REM Script to set up and run a Python project
REM Created by: <<(JAMAL_DH)>>
REM ========================================

REM Display a colored "Created by" message using PowerShell
powershell -command ^
    "Write-Host 'Secure Chat App => Demo Launcher' -ForegroundColor Yellow; " ^
    "Write-Host 'Created by: ' -NoNewline -ForegroundColor Yellow; " ^
    "Write-Host '<<(JAMAL_AlQbail, Mubarak Nabih, Ahmad Albwab)>>' -ForegroundColor Blue"

SETLOCAL ENABLEEXTENSIONS

:CHECK_ADMIN
REM --- Check for Administrator Privileges ---
net session >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~dpnx0\"' -Verb RunAs"
    exit /b
)

REM --- Set up Directories and Variables ---
SET "PROJECT_DIR=%~dp0"
SET "VENV_DIR=%PROJECT_DIR%\.venv"
SET "VENV_SCRIPTS=%VENV_DIR%\Scripts"
SET "PYTHON_EXEC=%VENV_SCRIPTS%\python.exe"
SET "REQUIREMENTS_FILE=%PROJECT_DIR%\requirment.txt"

REM --- Check if Python is Installed ---
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH. Please install Python and try again.
    pause
    exit /b 1
)

REM --- Create Virtual Environment if Not Exists ---
IF NOT EXIST "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM --- Upgrade pip ---
echo Upgrading pip to the latest version...
"%PYTHON_EXEC%" -m pip install --upgrade pip
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

REM --- Install/Upgrade Dependencies ---
IF EXIST "%REQUIREMENTS_FILE%" (
    echo Installing and upgrading dependencies from requirements.txt...
    "%PYTHON_EXEC%" -m pip install --upgrade -r "%REQUIREMENTS_FILE%"
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
) ELSE (
    echo Requirements file not found at "%REQUIREMENTS_FILE%".
    pause
    exit /b 1
)

REM --- Run the SCA demo via your inner script ---
echo Launching CustomTkinter demo…
call "%PROJECT_DIR%SCA\run_demo.bat"
IF %ERRORLEVEL% NEQ 0 (
    echo Demo script exited with errors.
    pause
    exit /b 1
)

pause
ENDLOCAL
