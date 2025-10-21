#!/bin/bash

# Script para iniciar el frontend en Linux/Ubuntu

echo "========================================"
echo "  Iniciando Frontend - Dashboard"
echo "========================================"
echo ""

cd "$(dirname "$0")/frontend" || exit 1

# Verificar si node_modules existe
if [ ! -d "node_modules" ]; then
    echo "[ADVERTENCIA] No se encontraron las dependencias de Node.js"
    echo "Instalando dependencias..."
    npm install
    echo ""
fi

echo ""
echo "Iniciando servidor de desarrollo Vite..."
echo "Dashboard disponible en: http://localhost:5173"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

npm run dev
