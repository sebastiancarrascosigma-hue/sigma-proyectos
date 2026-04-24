@echo off
title Sigma Proyectos — Detener
chcp 65001 >nul
echo.
echo  ============================================================
echo    Sigma Proyectos — Deteniendo servidor
echo  ============================================================
echo.

cd /d "%~dp0"

docker compose version >nul 2>&1
if %errorlevel%==0 (
    docker compose down
    echo.
    echo  Servidor detenido.
) else (
    taskkill /f /im uvicorn.exe >nul 2>&1
    taskkill /f /im python.exe /fi "WINDOWTITLE eq Sigma Proyectos*" >nul 2>&1
    echo  Proceso uvicorn detenido.
)

echo.
pause
