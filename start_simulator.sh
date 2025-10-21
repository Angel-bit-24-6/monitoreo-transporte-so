#!/bin/bash

# Script para iniciar el simulador GPS en Linux/Ubuntu

echo "========================================"
echo "  Iniciando Simulador GPS"
echo "========================================"
echo ""

cd "$(dirname "$0")/simulator" || exit 1

# Verificar si existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "[ADVERTENCIA] No se encontró el entorno virtual del simulador"
    echo "Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Instalando dependencias..."
    pip install -r requirements.txt
    echo ""
else
    source venv/bin/activate
fi

echo ""
echo "[IMPORTANTE] Asegúrate de haber configurado los tokens en device_config.json"
echo ""
echo "Iniciando simulador con renovación automática de tokens..."
echo "Intervalo de envío: 5 segundos"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

python3 gps_simulator_with_renewal.py -i 5
