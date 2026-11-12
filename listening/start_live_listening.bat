@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
echo ========================================================
echo   Starting Visible Live Listening Practice Runner
echo   Watch your Chrome window interact and solve live!
echo   Press Ctrl+C at any time in this window to stop.
echo ========================================================
python run_live.py
pause

