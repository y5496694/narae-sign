@echo off
cd /d "%~dp0"
pythonw signature.py %*
if errorlevel 1 (
  echo Python 3 and Pillow are required. Run: python -m pip install -r requirements.txt
  pause
)
