#!/bin/bash

# SE VERIFICA QUE PYTHON ESTE INSTALADO EN EL SISTEMA
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no está instalado en este sistema, instalalo."
    read -p "Presiona Enter para salir..."
    exit 1
fi

# SE VERIFICA QUE VENV ESTE INSTALADO EN EL SISTEMA
if ! python3 -c "import venv" &> /dev/null; then
    echo "[ERROR] El módulo 'venv' de Python no está instalado en tu sistema."
    echo "Esto es común en Linux Mint/Ubuntu. Por favor, abre una terminal normal e instala el paquete ejecutando:"
    echo "sudo apt install python3-venv"
    echo ""
    read -p "Presiona Enter para salir y realiza la instalación..."
    exit 1
fi

Carpetadedatos="GhostubeDATA"

# CAMBIAR DIRECTORIO A LA CARPETA DE DATOS
cd "$Carpetadedatos" || { 
    echo "[ERROR] No se encontró la carpeta $Carpetadedatos"
    read -p "Presiona Enter para salir..."
    exit 1 
}

# MENU
while true; do
    echo -e "\n================================================\n"
    echo -e "         Gestor del Servidor Multimedia \n"
    echo -e "================================================\n"
    echo -e " 1) Instalar dependencias (solo la primera vez)"
    echo -e " 2) Iniciar servidor"
    echo -e " 3) Salir \n"
    echo -e "================================================\n"
    read -p "Elige una opcion (1, 2 o 3): " opcion

    if [ "$opcion" == "1" ]; then
        echo "[+] Creando entorno virtual 'instalacion'..."
        # Comando de creacion del entorno virtual || Mensaje de error si el comando falla
        python3 -m venv instalacion || { echo "[ERROR] Falló la creación del entorno virtual."; continue; }
        
        echo "[+] Instalando dependencias, asegurate de tener internet..."
        instalacion/bin/pip install -r requirements.txt || { echo -e "\n\n\n\n\n\n[ERROR] Falló la instalación de dependencias."; continue; }
        
        echo "[!] Instalacion completada."

    elif [ "$opcion" == "2" ]; then
        # Esto solo verifica si existe el entorno virtual "instalacion" 
        if [ ! -f "instalacion/bin/python" ]; then
            echo "[ERROR] El entorno no existe o está corrupto. Por favor, ejecuta la opción 1 (Instalacion) y vuelve a intentar iniciar el servidor."
            continue
        fi
        
        echo "[+] Iniciando servidor..."
        instalacion/bin/python app.py

    elif [ "$opcion" == "3" ]; then
        echo "Saliendo..."
        exit 0
    else
        echo "Opcion no valida."
    fi
done
