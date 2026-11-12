@echo off
title BharatCraft - Autonomous Desktop Platform
color 0b

echo ======================================================================
echo  Launching BharatCraft Autonomous Suite
echo  Design:
echo   - Left Half:  BharatCraft AI Controller (PixelCraft Theme)
echo   - Right Half: Live Google Chrome Browser (Auto-Tiled)
echo ======================================================================
echo.

cd /d "%~dp0"
python desktop_app.py

if errorlevel 1 (
    echo.
    echo Platform encountered an error.
    pause
)
