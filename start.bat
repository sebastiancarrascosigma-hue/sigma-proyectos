@echo off
setlocal enabledelayedexpansion
title Sigma Proyectos
chcp 65001 >nul
echo.
echo  ============================================================
echo    Sigma Proyectos -- Iniciando servidor
echo  ============================================================
echo.

cd /d "%~dp0"

:: Verificar .env
if not exist ".env" (
    echo  [!] Archivo .env no encontrado.
    echo      Ejecuta primero: python scripts\setup.py
    echo.
    pause
    exit /b 1
)

:: Cargar variables del .env (ignora lineas con # y lineas vacias)
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /v "^#" .env`) do (
    if not "%%A"=="" set "%%A=%%B"
)

:: Puerto por defecto
if not defined PORT set PORT=8000

:: Detectar IP de ZeroTier
set ZT_IP=
for /f "tokens=*" %%i in ('zerotier-cli listnetworks 2^>nul ^| findstr /i "OK"') do (
    for /f "tokens=8" %%j in ("%%i") do (
        for /f "tokens=1 delims=/" %%k in ("%%j") do set ZT_IP=%%k
    )
)

:: Intentar Docker Compose primero
docker compose version >nul 2>&1
if %errorlevel%==0 (
    echo  Modo: Docker Compose
    echo.
    call :mostrar_urls
    docker compose up --build
    pause
    exit /b 0
)

echo  Modo: Entorno virtual Python
echo.

:: Entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo  Creando entorno virtual...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo  Verificando dependencias...
pip install -r requirements.txt -q

:: Crear directorio DB si usa OneDrive
if defined ONEDRIVE_DB_DIR (
    if not exist "%ONEDRIVE_DB_DIR%" mkdir "%ONEDRIVE_DB_DIR%"
    set DATABASE_URL=sqlite:///%ONEDRIVE_DB_DIR:\=/%/sigma_proyectos.db
)

:: Inicializar base de datos si no existe
if defined ONEDRIVE_DB_DIR (
    if not exist "%ONEDRIVE_DB_DIR%\sigma_proyectos.db" (
        echo  Inicializando base de datos...
        python -X utf8 seed_data.py
    )
) else (
    if not exist "sigma_proyectos.db" (
        echo  Inicializando base de datos...
        python -X utf8 seed_data.py
    )
)

call :mostrar_urls

python -X utf8 -m uvicorn main:app --host 0.0.0.0 --port %PORT% --reload
pause
exit /b 0

:: ---- subrutina URLs ----
:mostrar_urls
echo  ============================================================
echo    ACCESO AL SISTEMA
echo.
echo    Local (este equipo):
echo    http://localhost:%PORT%
echo.
if defined ZT_IP (
    echo    Red Sigma - ZeroTier ^(compartir con el equipo^):
    echo    http://%ZT_IP%:%PORT%
    echo.
) else (
    echo    [!] ZeroTier no detectado. Instala el cliente y une
    echo        el equipo a la red Sigma para acceso compartido.
    echo        Ver: scripts\unirse_a_sigma.txt
    echo.
)
echo    Visor HuggingFace ^(sistema separado, solo lectura^):
echo    https://sebas1989-sigma-proyectos.hf.space
echo.
echo    Presiona Ctrl+C para detener el servidor
echo  ============================================================
echo.
goto :eof
