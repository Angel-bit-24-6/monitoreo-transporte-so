@echo off
REM Script para iniciar el backend en Windows

echo ========================================
echo   Iniciando Backend - Sistema de Monitoreo
echo ========================================
echo.

cd /d "%~dp0backend"

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo [ERROR] No se encontro el entorno virtual
    echo Por favor, ejecuta primero:
    echo   cd backend
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Verificar archivo .env
if not exist ".env" (
    echo [ADVERTENCIA] No se encontro archivo .env
    echo Copiando desde .env.example...
    copy .env.example .env
    echo.
    echo [IMPORTANTE] Edita backend\.env con tus credenciales de PostgreSQL
    echo.
    pause
)

echo.
echo Iniciando servidor FastAPI...
echo Backend disponible en: http://localhost:8000
echo Documentacion API: http://localhost:8000/docs
echo.
echo Presiona Ctrl+C para detener
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
