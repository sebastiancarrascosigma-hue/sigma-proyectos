@echo off
title Sigma Proyectos - Servidor
echo.
echo  ============================================
echo   Sigma Proyectos - Iniciando servidor...
echo  ============================================
echo.

cd /d "%~dp0"

:: Verificar si existe el entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo  Creando entorno virtual...
    python -m venv venv
)

:: Activar entorno virtual
call venv\Scripts\activate.bat

:: Instalar dependencias si es necesario
echo  Verificando dependencias...
pip install -r requirements.txt -q

:: Cargar datos de demo si la base de datos no existe
if not exist "sigma_proyectos.db" (
    echo  Cargando datos de demostración...
    python -X utf8 seed_data.py
)

echo.
echo  ============================================
echo   Servidor corriendo en: http://localhost:8000
echo   Presiona Ctrl+C para detener
echo  ============================================
echo.

python -X utf8 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
