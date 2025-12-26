@echo off
cd /d "%~dp0"
python -m watchdog.watchmedo auto-restart --patterns="*.py" --recursive -- python main.py
pause
