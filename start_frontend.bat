@echo off
REM Script para iniciar el frontend en Windows

echo ========================================
echo   Iniciando Frontend - Dashboard
echo ========================================
echo.

cd /d "%~dp0frontend"

REM Verificar si node_modules existe
if not exist "node_modules\" (
    echo [ADVERTENCIA] No se encontraron las dependencias de Node.js
    echo Instalando dependencias...
    call npm install
    echo.
)

echo.
echo Iniciando servidor de desarrollo Vite...
echo Dashboard disponible en: http://localhost:5173
echo.
echo Presiona Ctrl+C para detener
echo.

call npm run dev

pause
