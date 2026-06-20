#!/bin/bash

# SE VERIFICA QUE PYTHON ESTE INSTALADO EN EL SISTEMA
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no está instalado en este sistema, usa el instalador oficial y agregalo al path de tu computadora."
    read -p "Presiona Enter para salir..."
    exit 1
fi

Carpetadedatos="GhostubeDATA"

# CAMBIAR DIRECTORIO A LA CARPETA DE DATOS
cd "$Carpetadedatos" || { 
    echo "[ERROR] No se encontró la carpeta $Carpetadedatos"
    read -p "Presiona Enter para salir..."
    exit 1 
}

echo "[!] Recuerda iniciar este script como administrador para la instalacion"
echo "sudo bash ./Linux_Install.sh"
# MENU
while true; do
    echo -e "\n================================================\n"
    echo -e "         Gestor del Servidor Multimedia \n"
    echo -e "================================================\n"
    echo -e " 1) Instalar dependencias (root)"
    echo -e " 2) Iniciar servidor"
    echo -e " 3) Configuraciones Avanzadas"
    echo ""
    echo -e " 0) Salir \n"
    echo -e "================================================\n"
    read -p "Elige una opcion: " opcion

if [ "$opcion" == "1" ]; then
        clear
        echo "========================================================"
        echo "      RESUMEN DE INSTALACION (REQUIERE: SUDO)  "
        echo "========================================================"
        echo " 1. Instalar modulo python3-venv (Entornos virtuales)"
        echo " 2. Crear entorno virtual e instalar requirements"
        echo " 3. Instalar servidor Caddy (si no lo está)"
        echo " 4. Desactivar el autoarranque de Caddy"
        echo " 5. Instalar FFmpeg para multimedia (si no lo está)"
        echo "========================================================"
        read -p "¿Deseas iniciar la instalacion ahora? (si/no): " confirmar

        # Verificamos si el usuario no escribió "si", "s" o "SI"
        if [[ "${confirmar,,}" != "si" && "${confirmar,,}" != "s" ]]; then
            echo "[!] Instalacion cancelada. Volviendo al menu..."
            sleep 2
            continue
        fi

        clear
        echo "================================================"
        echo " 1.- PREPARANDO ENTORNO VIRTUAL PYTHON"
        echo "================================================"
        if ! python3 -c "import venv" &> /dev/null; then
            echo "[+] Instalando paquete python3-venv..."
            sudo apt update
            sudo apt install -y python3-venv
        fi

        echo "[+] Creando entorno virtual 'instalacion'..."
        python3 -m venv instalacion || { echo "[ERROR] Falló la creación del entorno virtual."; sleep 3; continue; }
        
        echo "[+] Instalando dependencias de Python..."
        instalacion/bin/pip install -r requirements.txt || { echo "[ERROR] Falló la instalación de dependencias."; sleep 3; continue; }

        echo ""
        echo "================================================"
        echo " 2.- INSTALANDO SERVIDOR CADDY"
        echo "================================================"
        if ! command -v caddy &> /dev/null; then
            echo "[+] Instalando Caddy desde su repositorio oficial..."
            sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
            sudo apt update && sudo apt install -y caddy
        else
            echo "[+] Caddy ya está instalado en el sistema. Omitiendo descarga."
        fi

        echo ""
        echo "================================================"
        echo " 3.- CONFIGURANDO CADDY"
        echo "================================================"
        echo "[+] Desactivando el autoinicio de Caddy..."
        sudo systemctl stop caddy 2>/dev/null
        sudo systemctl disable caddy 2>/dev/null
        echo "[+] Autoinicio desactivado. Caddy solo despertara con Ghostube."

        echo ""
        echo "================================================"
        echo " 4.- COMPROBANDO FFMPEG"
        echo "================================================"
        if ! command -v ffmpeg &> /dev/null; then
            echo "[+] Instalando paquete FFmpeg..."
            sudo apt update
            sudo apt install -y ffmpeg
        else
            echo "[+] FFmpeg ya está instalado en el sistema. Omitiendo descarga."
        fi

        echo ""
        echo "================================================"
        echo " [!] INSTALACION COMPLETADA CON EXITO"
        echo "================================================"
        read -p "Presiona Enter para volver al menu..."

    elif [ "$opcion" == "2" ]; then
        # Esto solo verifica si existe el entorno virtual "instalacion" 
        if [ ! -f "instalacion/bin/python" ]; then
            echo "[ERROR] El entorno no existe o está corrupto. Por favor, ejecuta la opción 1 (Instalacion) y vuelve a intentar iniciar el servidor."
            continue
        fi
        
        echo "[+] Iniciando servidor flask..."
        instalacion/bin/python app.py &
        FLASK_PID=$!
        sleep 2

        PUERTO_CADDY=9090
        if [ -f "puertos.txt" ]; then
            PUERTO_EXTRAIDO=$(grep "^CADDY=" puertos.txt | cut -d'=' -f2)
            
            if [ -n "$PUERTO_EXTRAIDO" ]; then
                PUERTO_CADDY=$PUERTO_EXTRAIDO
            fi
        fi

        echo "==================================================="
        echo ""
        echo ""
        echo " ENTRA A ESTE ENLACE PARA SABER COMO USAR GHOSTUBE"
        echo "  http://localhost:$PUERTO_CADDY/ghostube"
        echo ""
        echo ""
        echo "==================================================="
        echo ""
        echo ""

        echo "[+] Iniciando servidor Caddy... (Presiona Ctrl+C para detener todo)"
        caddy run --config Caddyfile &
        CADDY_PID=$!

        # Esto le dice a Linux: "Si el usuario presiona Ctrl+C
        # intercepta la señal, ejecuta estas muertes precisas y luego sal del script".
        trap "echo -e '\n[!] Apagando este Ghostube...'; kill $FLASK_PID $CADDY_PID 2>/dev/null; exit" INT

        # Se quedará esperando hasta que presiones Ctrl+C y se active la trampa.
        wait $CADDY_PID

    elif [ "$opcion" == "3" ]; then
        while true; do
            clear
            echo "================================================"
            echo "           CONFIGURACIONES AVANZADAS            "
            echo "================================================"
            echo " 1) Modificar puertos"
            echo " 2) Aplicar configuraciones de puertos"
            echo ""
            echo " 0) Volver al menu principal"
            echo "================================================"
            read -p "Elige una opcion (1, 2 o 3): " sub_opcion

            if [ "$sub_opcion" == "1" ]; then
                # Si el archivo no existe, lo creamos con los valores por defecto antes de abrir nano
                if [ ! -f "puertos.txt" ]; then
                    echo "CADDY=9090" > puertos.txt
                    echo "FLASK=9091" >> puertos.txt
                    echo "CADDY_ADMIN=2019" >> puertos.txt
                fi
                # Abrimos nano para que el usuario edite
                nano puertos.txt

            elif [ "$sub_opcion" == "2" ]; then
                clear
                # Ejecutamos a nuestro "Portero"
                instalacion/bin/python Doorman.py
                
                # Imprimimos la advertencia roja/llamativa
                echo "Los puertos se han actualizado y el servidor se ha reconfigurado."
                echo "Si ya tenias videos agregados:"
                echo "Dirigete a el panel de configuraciones y simplemente presiona el boton 'Guardar cambios de carpetas'."
                echo " Esto te permitira volver a ver tus videos sin problemas"
                echo ""
                echo ""
                read -p "Presiona Enter para volver al submenu..."

            elif [ "$sub_opcion" == "0" ]; then
                # El comando break rompe el bucle interno y te regresa al menu principal
                break
            else
                echo "[ERROR] Opcion no valida."
                sleep 2
            fi
        done

    elif [ "$opcion" == "0" ]; then
        echo "Saliendo..."
        exit 0
    else
        echo "Opcion no valida."
    fi
done
