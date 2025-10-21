@echo off
REM Script para iniciar todos los servicios en Windows

echo ========================================
echo   Sistema de Monitoreo de Transporte
echo   Iniciando Todos los Servicios
echo ========================================
echo.

echo [1/3] Iniciando Backend...
start "Backend - FastAPI" cmd /k "%~dp0start_backend.bat"
timeout /t 5 /nobreak > nul

echo [2/3] Iniciando Frontend...
start "Frontend - Dashboard" cmd /k "%~dp0start_frontend.bat"
timeout /t 3 /nobreak > nul

echo [3/3] Iniciando Simulador GPS...
start "Simulador GPS" cmd /k "%~dp0start_simulator.bat"

echo.
echo ========================================
echo   Todos los servicios iniciados
echo ========================================
echo.
echo Backend:    http://localhost:8000/docs
echo Frontend:   http://localhost:5173
echo Simulador:  Ventana separada
echo.
echo Cierra las ventanas individuales para detener cada servicio
echo.
pause
