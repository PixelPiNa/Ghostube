@echo off
title Gestor del Servidor Multimedia Ghostube
chcp 65001 > nul

:: 1. VERIFICACION DE PYTHON
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no fue agregado a las variables de entorno ^(PATH^).
    echo Por favor, descarga e instala Python desde python.org antes de continuar.
    echo Busca un tutorial sobre como instalar python si tienes dudas.
    pause
    exit /b
)

set CARPETA_PROYECTO=GhostubeDATA


echo ==============================================
echo    Gestor del Servidor Multimedia Ghostube    
echo ==============================================
echo 1) Instalacion (Crear entorno y dependencias)
echo 2) Iniciar servidor
echo ==============================================
set /p opcion="Elige una opcion (1 o 2):  "

:: 2. ENTRADA A LA CARPETA
cd "%CARPETA_PROYECTO%" || (
    echo [ERROR] No se encontro la carpeta %CARPETA_PROYECTO%.
    pause
    exit /b
)

:: 3. LÓGICA DEL MENÚ
if "%opcion%"=="1" (
    echo [+] Creando entorno virtual "instalacion"...
    python -m venv instalacion
    echo [+] Instalando dependencias...
    instalacion\Scripts\pip install -r requirements.txt
    echo [!] Instalacion completada. Ya puedes iniciar el servidor.
    pause
) else if "%opcion%"=="2" (
    echo [+] Iniciando servidor...
    instalacion\Scripts\python app.py
    pause
) else (
    echo Opcion no valida.
    pause
)