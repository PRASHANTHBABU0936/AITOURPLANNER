 @echo off
title AI Tour Planner
cd /d "%~dp0"

echo ====================================
echo       AI TOUR PLANNER
echo ====================================

echo.
echo [1/2] Building latest Docker image...
docker build -t ai-tour-planner:latest .

if errorlevel 1 (
    echo Docker build failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Starting AI Tour Planner...
docker run --rm -p 8501:8501 --env-file .env ai-tour-planner:latest

echo.
echo Docker stopped or exited with an error.
pause