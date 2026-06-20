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
echo [+] Python vinculado
echo.
echo.

cd "GhostubeDATA" || (
    echo [ERROR] No se encontro GhostubeDATA.
    pause
    exit /b
)
cls

:menu
cls
echo ================================================
echo.                                               
echo          Gestor del Servidor Multimedia         
echo.
echo ================================================
echo.
echo  1) Instalar dependencias (solo la primera vez)
echo  2) Iniciar servidor
echo  3) Configuraciones Avanzadas
echo.
echo  0) Salir
echo.
echo ================================================
echo.
echo.
set /p opcion="Elige una opcion: "

if "%opcion%"=="1" goto op_instalar
if "%opcion%"=="2" goto op_iniciar
if "%opcion%"=="3" goto submenu
if "%opcion%"=="0" exit /b
cls
echo [ERROR] Opcion no valida.
timeout /t 2 > nul
goto menu






:op_instalar
cls
echo [+] Creando entorno virtual "instalacion"...
python -m venv instalacion
echo [+] Instalando dependencias...
instalacion\Scripts\pip install -r requirements.txt
cls
echo [!] Instalacion completada.
pause
goto menu




:op_iniciar
cls
echo [+] Iniciando servidor flask...
start /b instalacion\Scripts\python app.py
timeout /t 2 /nobreak > nul

echo [+] Iniciando servidor Caddy...
start /b extenzzziones\caddy.exe run --config Caddyfile
timeout /t 2 /nobreak > nul
echo.
echo.

set PUERTO_CADDY=9090
if exist "puertos.txt" (
    for /f "tokens=1,2 delims==" %%a in (puertos.txt) do (
        if /i "%%a"=="CADDY" set PUERTO_CADDY=%%b
    )
)

echo =======================================================================
echo.
echo.
echo  ENTRA A ESTE ENLACE DESDE ESTA COMPUTADORA PARA SABER COMO USAR GHOSTUBE
echo   http://localhost:%PUERTO_CADDY%/ghostube
echo.
echo.
echo =======================================================================
echo   Para apagar el servidor: presiona Ctrl+C y cierra esta ventana.
echo.
pause > nul
goto menu





:submenu
cls
echo ================================================
echo               CONFIGURACIONES AVANZADAS
echo ================================================
echo.
echo  1) Modificar puertos (editar txt)
echo  2) Aplicar configuraciones de puertos
echo.
echo  0) Volver al menu principal
echo.
echo ================================================
echo.
set /p sub_opcion="Elige una opcion: "

if "%sub_opcion%"=="1" goto sub_modificar
if "%sub_opcion%"=="2" goto sub_aplicar
if "%sub_opcion%"=="0" goto menu

echo [ERROR] Opcion no valida.
timeout /t 2 > nul
goto submenu






:sub_modificar
if not exist "puertos.txt" (
    echo CADDY=9090> puertos.txt
    echo FLASK=9091>> puertos.txt
    echo CADDY_ADMIN=2019>> puertos.txt
)
echo [+] Abriendo puertos.txt... Guarda y cierra para continuar.
notepad puertos.txt
goto submenu




:sub_aplicar
cls
if not exist "instalacion\Scripts\python.exe" (
    echo [ERROR] Necesitas INSTALAR antes de modificar puertos.
    pause
    goto submenu
)

instalacion\Scripts\python Doorman.py

cls
echo  [!] Los puertos se han actualizado y el servidor se ha reconfigurado.
echo.
echo  Si ya tenias videos agregados:
echo  Dirigete a el panel de configuraciones y simplemente presiona el boton 'Guardar cambios de carpetas'.
echo  Esto te permitira volver a ver tus videos sin problemas
echo.
echo =======================================================================
echo.
pause
goto submenu