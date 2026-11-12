@echo off
title Bharat English Autonomous IDE (VS Code Edition)
color 0b

echo ======================================================================
echo  Launching Bharat English Autonomous Platform (VS Code Style)
echo  Features:
echo   - Left Pane: AI Controller, Progress Tracker, Ollama Thoughts & Terminal
echo   - Right Pane: Live Embedded Chrome Preview
echo ======================================================================
echo.

cd /d "%~dp0"
python desktop_app.py

if errorlevel 1 (
    echo.
    echo Platform encountered an error.
    pause
)
