@echo off
title VX Player PC
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo ----------------------------------------
    echo VX Player PC exited with an error.
    echo ----------------------------------------
    pause
)
