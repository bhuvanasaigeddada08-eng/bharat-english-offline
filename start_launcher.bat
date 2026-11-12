@echo off
title Bharat English Autonomous Suite Launcher
color 0b

cd /d "%~dp0"
python launcher.py

if errorlevel 1 (
    echo.
    echo Launcher encountered an error.
    pause
)
