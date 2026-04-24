@echo off
title Sigma Proyectos
chcp 65001 >nul
echo.
echo  ============================================================
echo    Sigma Proyectos — Iniciando servidor
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

:: Cargar variables del .env
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "line=%%A"
    if not "!line:~0,1!"=="#" (
        if not "%%A"=="" set "%%A=%%B"
    )
)

:: Intentar Docker Compose primero
docker compose version >nul 2>&1
if %errorlevel%==0 (
    echo  Modo: Docker Compose
    echo.
    docker compose up --build
    pause
    exit /b 0
)

echo  Docker no encontrado. Usando entorno virtual Python.
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

:: Cargar datos iniciales si no existe la base de datos
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

echo.
echo  ============================================================
echo    Servidor en: http://localhost:%PORT%
echo    Presiona Ctrl+C para detener
echo  ============================================================
echo.

python -X utf8 -m uvicorn main:app --host 0.0.0.0 --port %PORT% --reload
pause
