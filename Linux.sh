#!/bin/bash

# 1. VERIFICACIÓN DE PYTHON
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no está instalado en este sistema."
    echo "Por favor, instálalo ejecutando:         sudo apt install python3 python3-venv"
    read -p "Presiona Enter para salir..."
    exit 1
fi

CARPETA_PROYECTO="GhostubeDATA"

echo "====================================="
echo "   Gestor del Servidor Multimedia    "
echo "====================================="
echo "1) Instalación (Crear entorno y dependencias)"
echo "2) Iniciar servidor"
echo "====================================="
read -p "Elige una opción (1 o 2): " opcion

# 2. ENTRADA A LA CARPETA
cd "$CARPETA_PROYECTO" || { 
    echo "[ERROR] No se encontró la carpeta $CARPETA_PROYECTO"
    read -p "Presiona Enter para salir..."
    exit 1 
}

# 3. LÓGICA DEL MENÚ
if [ "$opcion" == "1" ]; then
    echo "[+] Creando entorno virtual 'instalacion'..."
    python3 -m venv instalacion
    echo "[+] Instalando dependencias..."
    instalacion/bin/pip install -r requirements.txt
    echo "[!] Instalación completada. Ya puedes iniciar el servidor."
    read -p "Presiona Enter para salir..."

elif [ "$opcion" == "2" ]; then
    echo "[+] Iniciando servidor..."
    instalacion/bin/python app.py

else
    echo "Opción no válida."
fi