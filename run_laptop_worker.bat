@echo off
title VX Player - Laptop Subtitle Worker (AMD Ryzen 5 3500U)
echo =======================================================
echo   VX Player - Laptop Subtitle Worker Companion
echo   CPU: AMD Ryzen 5 3500U (4 Cores, 8 Threads, AVX2)
echo =======================================================
echo.
cd /d "%~dp0"
python vx_laptop_worker.py %*
if errorlevel 1 (
    echo.
    echo Worker encountered an error. Press any key to exit.
    pause >nul
)
