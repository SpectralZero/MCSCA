@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: 1) Configuration
set "GTK_EXE_URL=https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
set "GTK_EXE_NAME=gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
set "INSTALL_DIR=C:\GTK"

:: 2) Download the installer if it’s not already here
if not exist "%~dp0%GTK_EXE_NAME%" (
    echo [INFO] Downloading GTK3 runtime installer...
    powershell -NoProfile -Command ^
      "try { Invoke-WebRequest -Uri '%GTK_EXE_URL%' -OutFile '%~dp0%GTK_EXE_NAME%' -UseBasicParsing } catch { exit 1 }"

    if errorlevel 1 (
        echo [ERROR] Failed to download %GTK_EXE_NAME%.
        exit /b 1
    )
)

:: 3) Run the installer silently
echo [INFO] Installing GTK3 runtime to %INSTALL_DIR% ...
start /wait "" "%~dp0%GTK_EXE_NAME%" ^
    /S ^                    :: silent mode :contentReference[oaicite:0]{index=0}
    /sideeffects=no ^       :: don’t register anywhere :contentReference[oaicite:1]{index=1}
    /dllpath=root ^          :: place DLLs in root of install dir :contentReference[oaicite:2]{index=2}
    /translations=no ^       :: skip language files :contentReference[oaicite:3]{index=3}
    /D=%INSTALL_DIR%         :: target directory (no quotes!)

if errorlevel 1 (
    echo [ERROR] GTK3 installation failed.
    exit /b 1
)

echo [SUCCESS] GTK3 runtime installed at %INSTALL_DIR%.
ENDLOCAL