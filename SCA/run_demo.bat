@echo off
cd /d %~dp0
REM --- Install GUI deps on first run ---
REM --- Launch the CustomTkinter demo UI ---
:: "%VENV_SCRIPTS%\python.exe" -m ctk_gui.launcher
 py -m ctk_gui.launcher