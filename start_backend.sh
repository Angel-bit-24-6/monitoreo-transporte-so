#!/bin/bash

# Script para iniciar el backend en Linux/Ubuntu

echo "========================================"
echo "  Iniciando Backend - Sistema de Monitoreo"
echo "========================================"
echo ""

cd "$(dirname "$0")/backend" || exit 1

# Verificar si existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "[ERROR] No se encontró el entorno virtual"
    echo "Por favor, ejecuta primero:"
    echo "  cd backend"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Verificar archivo .env
if [ ! -f ".env" ]; then
    echo "[ADVERTENCIA] No se encontró archivo .env"
    echo "Copiando desde .env.example..."
    cp .env.example .env
    echo ""
    echo "[IMPORTANTE] Edita backend/.env con tus credenciales de PostgreSQL"
    echo ""
    read -p "Presiona Enter para continuar..."
fi

echo ""
echo "Iniciando servidor FastAPI..."
echo "Backend disponible en: http://localhost:8000"
echo "Documentación API: http://localhost:8000/docs"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
