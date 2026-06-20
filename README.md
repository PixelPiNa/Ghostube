# Ghostube
Ghostube es un servidor web hecho en Flask que permite levantar tu propio sitio de video local basado en Tags.
Este proyecto busca brindarte una experiencia muy comoda para ver tus propios videos con tu propio servidor ¡Totalmente local y aislado del internet!.
Hecho especificamente para esas personas que buscan una alternativa decente para la visualizacion de su propio contenido a traves de una interfaz visual intuitiva, amigable e interactiva.

# ¿Que necesita para funcionar?
- **Python3**: Este proyecto fue programado en Python3.13, necesita de que tengas Python instalado para poder funcionar (Las dependencias las instala *Linux_Install.sh* o *Windows Install.bat* de forma automatica)
- **Ffmpeg**: aunque es opcional, la funcion de duracion del video lo requiere, así como la funcion de extraer miniaturas. (En el archivo comprimido se incluyen *ffmpeg.exe* y *ffprobe.exe* para funcionar en windows. En el caso de linux, *Linux_Install.sh* se encarga de instalarlos en tu sistema por tí). https://ffmpeg.org/download.html
- **Caddy Server**: Es el servidor que se encarga de escupirte los videos para que Flask no tenga que hacer el trabajo, ya que es muy lento a comparacion de caddy. En este caso Flask se encarga de las interfaces y Caddy de los videos. (En el archivo comprimido se incluye *caddy.exe* para funcionar en windows. En el caso de linux, *Linux_Install.sh* se encarga de instalarlo en tu sistema por tí). https://caddyserver.com/
- **Windows o Alguna distribucion derivada de Ubuntu (Linux Mint, Zorin OS, Ubuntu, etc.)**: Los orquestadores *Linux_Install.sh* y *Windows Install.bat* estan programados para esos sistemas operativos, jamás he usado algo fuera de ubuntu, entonces no sé si funcionará en otras distribuciones.

# ¿Como usar?
1. Este proyecto incluye dos orquestadores: *Linux_Install.sh* y *Windows Install.bat*; cada uno se encarga de instalar o iniciar el servidor, Deberás iniciar el que sea de tu respectivo sistema operativo.
2. Una vez iniciado el orquestador correspondiente, deberás seleccionar la opcion **1) instalar dependencias**
3. Despues de terminado el proceso de instalación, deberás seleccionar la opcion **2) iniciar servidor**
4. En la linea de comandos verás un mensaje como este donde deberas hacer Ctrl + Click:
```
ENTRA A ESTE ENLACE DESDE ESTA COMPUTADORA PARA SABER COMO USAR GHOSTUBE
http://localhost:9090/ghostube
```
5. Una vez entres a ese enlace desde la misma computadora donde estás iniciando el servidor, en pantalla verás un link como "http://192.168.1.###:9090", ese es el link con el que entraras a Ghostube en todos tus dispositivos locales (¡Solo dentro de tu casa!)
6. ¿Ya entraste? ¡Bien! Una vez dentro del servidor, dirigete al panel de configuraciones (es un engranaje rojo en la parte superior derecha) y en la primera seccion "Agrega tus carpetas" deberás agregar la **ruta absoluta de tu carpeta** (se ve algo como *C:\Users\TuUsuario\Videos\Peliculas* en windows; y algo como */home/TuUsuario/Videos/Peliculas* en linux). Y acto seguido pulsar el boton rojo de "Guardar Carpeta"
7. ¡Listo! Presiona las letras pequeñas que dicen "Volver al cine" (estan arriba a la izquierda) y ya puedes ver tus videos!!!

# Funciones
- **Ver todos los archivos de tu computadora y discos duros:** Autodescriptivo, ¡además tienes la seguridad de que los datos se conservarán aunque desconectes los discos duros! (para borrar los dispositivos de almacenamiento desconectados explora la seccion de "Mantenimiento" dentro del panel de configuraciones del servidor).
- **Aplicar tags a los videos:** ¡¡¡Puedes categorizar de varias maneras todos tus videos!!!
- **Opciones de busqueda:** Puedes elegir si limitar la busqueda a solo mostrar los resultados que contengan todos los tags en la barra de busqueda, o expandirla para buscar todos los videos que contengan alguno de los tags en la barra de busqueda. O en lugar de solo tags, ¡puedes buscar por medio de el titulo del video!
- **Ordena los videos por orden alfabetico o orden de agregacion al servidor:** Autodescriptivo.
- **Libertad para previsualizar tus videos como quieras:** ¿Prefieres que te muestre un clip del video cuando pasas el mouse por encima o en cambio mostrarlo como 5 diapositivas?.
- **Control parental:** Puedes bloquear ciertas secciones de la pagina detrás de una contraseña.
- **Ocultar Tags:** Los videos con *tags ocultos* no se mostraran por ningun lado a menos que escribas exactamente el nombre del tag en el buscador.
- **Autoetiquetado por carpetas:** ¿Tienes cientos de videos? Pues te otorgo la posibilidad de aplicar tags a carpetas completas.

## ¿Quieres acceder al servidor desde fuera de tu casa?
¡Te recomiendo usar Tailscale para esa tarea! No puedo hacer más que recomendartelo.
(No es recomendable dejar un puerto abierto al internet).

# Gracias por usar, recuerda apoyarme de cualquier manera!