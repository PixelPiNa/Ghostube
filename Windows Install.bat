@echo off
title Gestor del Servidor Multimedia
chcp 65001 > nul

echo [+] VERIFICACION DE PYTHON
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no fue agregado a las variables de entorno ^(PATH^).
    echo Por favor, descarga e instala Python desde python.org antes de continuar.
    pause
    exit /b
)
echo [+] Python instalado
echo.
echo.

cd "GhostubeDATA" || (
    echo [ERROR] No se encontro GhostubeDATA.
    pause
    exit /b
)
cls
:menu
echo ================================================
echo.                                               
echo          Gestor del Servidor Multimedia         
echo.
echo ================================================
echo.
echo  1) Instalar dependencias (solo la primera vez)
echo  2) Iniciar servidor
echo  3) Salir
echo.
echo ================================================
echo.
echo.
set /p opcion="Elige una opcion: "

if "%opcion%"=="1" (
    echo [+] Creando entorno virtual "instalacion"...
    python -m venv instalacion
    echo [+] Instalando dependencias...
    instalacion\Scripts\pip install -r requirements.txt
    cls
    echo [!] Instalacion completada.
    goto menu
) else if "%opcion%"=="2" (
    cls
    echo [+] Iniciando servidor flask...
    start /b instalacion\Scripts\python app.py
    timeout /t 2 /nobreak > nul

    echo [+] Iniciando servidor Caddy...
    start /b extenzzziones\caddy.exe run --config Caddyfile
    timeout /t 2 /nobreak > nul
    echo.
    echo.

    echo ===================================================
    echo  ENTRA A ESTE ENLACE PARA SABER COMO USAR GHOSTUBE
    echo   http://localhost:9090/ghostube
    echo ===================================================
    echo   Para apagar el servidor: presiona Ctrl+C y
    echo   cierra esta ventana.
    echo.

) else if "%opcion%"=="3" (
    exit /b
) else (
    cls
    echo [ERROR] Opcion no valida.
    goto menu
)
