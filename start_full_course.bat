@echo off
title Bharat English Full Autonomous Runner (Listening - Reading - Writing)
color 0a

echo ========================================================
echo  Starting Bharat English Full Sequential Autonomous Runner
echo  Pipeline: Listening (30) -^> Reading (30) -^> Writing (30)
echo ========================================================
echo.

cd /d "%~dp0"
python run_full_course.py

echo.
echo ========================================================
echo  Runner execution completed.
echo ========================================================
pause
