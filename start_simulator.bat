@echo off
REM Script para iniciar el simulador GPS en Windows

echo ========================================
echo   Iniciando Simulador GPS
echo ========================================
echo.

cd /d "%~dp0simulator"

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo [ADVERTENCIA] No se encontro el entorno virtual del simulador
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Instalando dependencias...
    pip install -r requirements.txt
    echo.
) else (
    call venv\Scripts\activate.bat
)

echo.
echo [IMPORTANTE] Asegurate de haber configurado los tokens en device_config.json
echo.
echo Iniciando simulador con renovacion automatica de tokens...
echo Intervalo de envio: 5 segundos
echo.
echo Presiona Ctrl+C para detener
echo.

python gps_simulator_with_renewal.py -i 5

pause
