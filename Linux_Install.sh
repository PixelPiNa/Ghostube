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
    echo "Esto es común en Ubuntu. Por favor, abre una terminal normal e instala el paquete ejecutando:"
    echo ""
    echo "sudo apt install python3-venv"
    echo ""
    read -p "Presiona Enter para salir y realiza la instalación..."
    exit 1
fi

# SE VERIFICA QUE CADDY ESTE INSTALADO EN EL SISTEMA
if ! command -v caddy &> /dev/null; then
    clear
    echo "[ERROR] Caddy no está instalado o no está en las variables de entorno (PATH)."
    echo "Para instalarlo en distribuciones basadas en Ubuntu, ejecuta los comandos oficiales de Caddy:"
    echo ""
    echo "sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl"
    echo "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg"
    echo "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list"
    echo "sudo apt update && sudo apt install caddy"
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
        
        clear
        echo "[!] Instalacion completada."

    elif [ "$opcion" == "2" ]; then
        # Esto solo verifica si existe el entorno virtual "instalacion" 
        if [ ! -f "instalacion/bin/python" ]; then
            echo "[ERROR] El entorno no existe o está corrupto. Por favor, ejecuta la opción 1 (Instalacion) y vuelve a intentar iniciar el servidor."
            continue
        fi
        
        echo "[+] Iniciando servidor flask..."
        instalacion/bin/python app.py
        FLASK_PID=$!
        sleep 2

        echo "==================================================="
        echo " ENTRA A ESTE ENLACE PARA SABER COMO USAR GHOSTUBE"
        echo "  http://localhost:9090/ghostube"
        echo "==================================================="
        echo ""

        echo "[+] Iniciando servidor caddy... (Presiona Ctrl+C para detener todo)"
        caddy run --config Caddyfile

        echo ""
        echo "[!] Deteniendo el backend de Flask (Limpieza de procesos)..."
        kill $FLASK_PID 2>/dev/null
        sleep 1

    elif [ "$opcion" == "3" ]; then
        echo "Saliendo..."
        exit 0
    else
        echo "Opcion no valida."
    fi
done
