from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Ubicacion, Tag, Video, Configuracion
import os
import platform
import subprocess
import threading
from flask import current_app

config_bp = Blueprint('config', __name__)

# --- CONFIGURACION DE RED ---
PUERTO_CADDY = 9090
PUERTO_FLASK = 9091
PUERTO_CADDY_ADMIN = 2019
# --- FIN CONFIGURACION ---


# ----------------------------------------------------- Ver si esto es windos o linus pa usar ffmpeg
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

if platform.system() == 'Windows':
    FFMPEG_CMD = os.path.join(BASE_DIR, 'extenzzziones', 'ffmpeg.exe')
    FFPROBE_CMD = os.path.join(BASE_DIR, 'extenzzziones', 'ffprobe.exe')
else:
    FFMPEG_CMD = 'ffmpeg'
    FFPROBE_CMD = 'ffprobe'


# -----------------------------------------------------RUTAS
@config_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        config_pass = Configuracion.query.filter_by(clave='pass_maestra').first()
        
        if not config_pass or not config_pass.valor or check_password_hash(config_pass.valor, password):
            session['admin_logged_in'] = True 
            
            # Leemos si el guardian dejo anotada una ruta. 'pop' la lee y la borra de la memoria.
            ruta_pendiente = session.pop('next_url', None)
            
            if ruta_pendiente:
                return redirect(ruta_pendiente) # Te manda a donde querias ir
            else:
                return redirect(url_for('inicio')) # Si no habia ruta, te manda al inicio
        else:
            return "Contraseña incorrecta <br><br> <a href='/login'>Intentar de nuevo</a>"
            
    return render_template('login.html')




# -----------------------------------------------------panel

@config_bp.route('/panel')
def panel():
    
    ubicaciones = Ubicacion.query.all()
    tags = Tag.query.all()
    
    # 1. Leer todas las configuraciones para enviarlas al HTML
    configs = {c.clave: c.valor for c in Configuracion.query.all()}
    
    return render_template('configuraciones.html', 
                           ubicaciones=ubicaciones, 
                           tags=tags,
                           modo_actual=configs.get('modo_miniaturas', 'dinamico'),
                           b_general=configs.get('bloqueo_general') == 'True',
                           b_explorar=configs.get('bloqueo_explorar') == 'True',
                           b_config=configs.get('bloqueo_configuraciones') == 'True',
                           b_sensible=configs.get('ocultar_sensible') == 'True')

# -----------------------------------------------------seguridad

@config_bp.route('/guardar_seguridad', methods=['POST'])
def guardar_seguridad():
    
    # Guardar o actualizar la contraseña
    nueva_pass = request.form.get('pass_maestra')
    if nueva_pass:
        config_pass = Configuracion.query.filter_by(clave='pass_maestra').first()
        # Encriptamos la contraseña antes de guardarla
        config_pass.valor = generate_password_hash(nueva_pass)

    # Guardar los interruptores (Checkboxes nativos)
    opciones_seguridad = {
        'bloqueo_general': 'True' if request.form.get('bloqueo_general') == 'on' else 'False',
        'bloqueo_explorar': 'True' if request.form.get('bloqueo_explorar') == 'on' else 'False',
        'bloqueo_configuraciones': 'True' if request.form.get('bloqueo_configuraciones') == 'on' else 'False',
        'ocultar_sensible': 'True' if request.form.get('ocultar_sensible') == 'on' else 'False'
    }

    for clave, nuevo_valor in opciones_seguridad.items():
        config_db = Configuracion.query.filter_by(clave=clave).first()
        if config_db:
            config_db.valor = nuevo_valor
            
    db.session.commit()
    return redirect(url_for('config.panel'))


@config_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('inicio'))

# ----------------------------------------------------- Configuraciones

# Gestión de Carpetas (Sobrenombres y Activar/Desactivar/Agregar)
@config_bp.route('/guardar_ubicaciones', methods=['POST'])
def guardar_ubicaciones():

    # Editar una carpeta existente
    ubicaciones = Ubicacion.query.all()
    for ubi in ubicaciones:
        # Actualizar nombre de las carpetasd
        nuevo_nombre = request.form.get(f'nombre_{ubi.id}')
        if nuevo_nombre:
            ubi.nombre = nuevo_nombre
        
        # Actualizar 
        esta_activa = request.form.get(f'activa_{ubi.id}') == 'on'
        ubi.activa = esta_activa

        # Cambia el color del tag con el que se muestra
        nuevo_color = request.form.get(f'color_{ubi.id}')
        if nuevo_color:
            ubi.color = nuevo_color

        # Eliminar
        if request.form.get(f'borrar_{ubi.id}') == 'on':
            db.session.delete(ubi)

    # Agregar una nueva carpeta
    nueva_ruta = request.form.get('nueva_ruta')
    if nueva_ruta and os.path.exists(nueva_ruta):
        nombre_defecto = os.path.basename(nueva_ruta)
        nueva_ubi = Ubicacion(ruta=nueva_ruta, nombre=nombre_defecto, activa=True)
        db.session.add(nueva_ubi)

    db.session.commit()
    actualizar_caddyfile()
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- LISTA NEGRA DE TAGS
@config_bp.route('/guardar_tags', methods=['POST'])
def guardar_tags():
    
    tags = Tag.query.all()
    for tag in tags:
        # Checkbox para Ocultar el tag de la vista principal
        esta_oculto = request.form.get(f'oculto_{tag.id}') == 'on'
        tag.oculto = esta_oculto
        
    db.session.commit()
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- MANTENIMIENTO DE LA BDD 
@config_bp.route('/limpiar_basura', methods=['POST'])
def limpiar_basura():
    
    # Borrar Tags Huérfanos
    tags = Tag.query.all()
    tags_borrados = 0 #contador de tags borrados
    for tag in tags:
        # Si un tag no es utilizado en ningun video, se borra y ya w q mas qieres q pase
        if not tag.videos:
            db.session.delete(tag)
            tags_borrados += 1 #incrementar el tag de hace un momento
    
    db.session.commit()
    
    # Una limpieza simple de la base de datos para evitar que se abstraiga
    # Esta funcionreduce el tamaño del archivo .db si había mucho espacio vaacio
    db.session.execute(db.text("VACUUM"))
    db.session.commit() # Confirmamos el vacuum
    
    # Mensaje feedback que se verá en la consola
    print(f"--- Mantenimiento: {tags_borrados} tags huérfanos eliminados y DB optimizada. ---")
    
    return redirect(url_for('config.panel'))
# ----------------------------------------------------- PURGAR VIDEOS
# Cuando borras una carpeta completa, o desconectas una usb, el server piensa 
# "probablemente solo no puedo acceder a los datos temporalmente", así que deja los datos de esos videos en la BDD, 
# por si vuelven a aparecer algun dia.
# Con esta funcion eliminas definitivamente todos los videos que no se encuentren en este momento, 
# no importa si es por que la unidad de almacenamiento externa esta desconectada, 
# elimina todo lo relacionado de la base de datos.
# ----------------------------------------------------- PURGAR VIDEOS
@config_bp.route('/purgar_db', methods=['POST'])
def purgar_db():
    import os
    
    carpetas_borradas = 0
    videos_borrados = 0
    
    # ---- Limpia Carpetas y USBs desconectados
    # Revisamos todas las ubicaciones registradas
    ubicaciones = Ubicacion.query.all()
    for ubi in ubicaciones:
        if not os.path.exists(ubi.ruta):
            # Si la ruta ya no existe (USB desconectado o carpeta borrada), se borra.
            db.session.delete(ubi)
            carpetas_borradas += 1
            
    # Guardamos los cambios de esta eliminacion de carpetas antes de pasar a la eliminacion individual
    db.session.commit()
    
    # ---- Limpia videos solitos
    # Revisa si se desaparecio un archivo MP4 en tu sistema, pero la carpeta sigue ahi
    videos = Video.query.all()
    for video in videos:
        # También se limpian los videos huerfanos en general
        if not video.ubicacion_id or not os.path.exists(video.ruta_completa):
            db.session.delete(video)
            videos_borrados += 1
            
    db.session.commit()
    
    # ---- Ejecutamos un VACUUM para exprimir el archivo .db y hacerlo pesar menos
    db.session.execute(db.text("VACUUM"))
    db.session.commit()
    actualizar_caddyfile()
    
    print(f"--- PURGA COMPLETA: {carpetas_borradas} carpetas no encontradas y {videos_borrados} videos inexistentes eliminados.")
    
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- AUTOTAGGING POR CARPETAS
### Esta funcion funciona como un taggeador masivo, que le agregara las mismas etiquetas a todo el contenido multimedia de una carpeta

@config_bp.route('/detectar_carpetas', methods=['GET'])
def detectar_carpetas():
    
    # ---Extensiones para saber si una carpeta vale la pena mostrarla
    # avi solo está acá para joder, algunos usuarios tienen películas en ese formato, como mi padre
    # pero no funcionan en algunos navegadores
    # te extraño apá
    ext_validas = ('.mp4', '.mkv', '.avi', '.jpg', '.png', '.jpeg')
    
    lista_carpetas = []
    
    # solo se muestran las ubicaciones activas que configuraste
    #si es que configuraste algo luser
    ubicaciones = Ubicacion.query.filter_by(activa=True).all()
    
    for ubi in ubicaciones:
        if not os.path.exists(ubi.ruta): continue
        
        # os.walk recorre todo el arbol de directorios
        for raiz, carpetas, archivos in os.walk(ubi.ruta):
            # se cuentan cuantos archivos multimedia hay en ESTA carpeta (sin contar la subcarpetas dentro)
            cantidad = sum(1 for f in archivos if f.lower().endswith(ext_validas))
            
            if cantidad > 0:
                # Si la carpeta tiene multimedia valido, la agrega a la lista
                lista_carpetas.append({
                    'ruta': raiz,
                    'cantidad': cantidad
                })
    
    # Ordenamos alfabeticamente para que sea facil de leer
    lista_carpetas.sort(key=lambda x: x['ruta'])
    
    # Renderizamos la misma página pero enviándole esta lista nueva
    return render_template('configuraciones.html', 
                           ubicaciones=ubicaciones, # Necesario para la tabla de arriba
                           tags=Tag.query.all(),    # necesario para la lista negra
                           carpetas_detectadas=lista_carpetas) ### DATOS NUEVOS

# ----------------------------------------------------- AUTOTAGS MASIVOS
@config_bp.route('/aplicar_autotags', methods=['POST'])
def aplicar_autotags():
    
    rutas = request.form.getlist('rutas_carpeta')
    nombres_tags_raw = request.form.getlist('nombres_tags')
    
    videos_afectados = 0
    tags_creados = 0
    
    for ruta, string_tags in zip(rutas, nombres_tags_raw):
        # Si el campo esta vacio, pasamos a la siguiente carpeta
        if not string_tags.strip():
            continue
            
        
        try:
            import json
            datos_tagify = json.loads(string_tags)
            tags_separados = [item['value'].strip() for item in datos_tagify]
        except:
            # Fallback por si llega texto plano
            tags_separados = [t.strip() for t in string_tags.split(',')]
        
        # Ahora se procesa cada tag individualmente
        for nombre_tag in tags_separados:
            if not nombre_tag: continue
            
            # Buscar o Crea el Tag
            tag_db = Tag.query.filter_by(nombre=nombre_tag).first()
            if not tag_db:
                tag_db = Tag(nombre=nombre_tag)
                db.session.add(tag_db)
                tags_creados += 1
            
            # Busca videos y aplica
            videos_en_carpeta = Video.query.all()
            for video in videos_en_carpeta:
                import os # Asegurarnos de que OS esté disponible
                if os.path.dirname(video.ruta_completa) == ruta:
                    if tag_db not in video.tags:
                        video.tags.append(tag_db)
                        videos_afectados += 1
    
    db.session.commit()
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- MODO DE AUTOVISUALIZACION DE MINIATURAS
@config_bp.route('/guardar_modo_visual', methods=['POST'])
def guardar_modo_visual():
    
    nuevo_modo = request.form.get('modo_miniaturas')
    config = Configuracion.query.filter_by(clave='modo_miniaturas').first()
    
    # el nuevo valor va a la tabla general
    if config:
        config.valor = nuevo_modo
    else:
        nueva_config = Configuracion(clave='modo_miniaturas', valor=nuevo_modo)
        db.session.add(nueva_config)
        
    db.session.commit()
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- proceso secundario de las miniaturas

def procesar_miniaturas_background(app_context):
    """Esta función corre en segundo plano para no congelar la página web."""
    with app_context:
        from app import app, db, Video
        carpeta_miniaturas = os.path.join(app.root_path, 'static', 'miniaturas')
        os.makedirs(carpeta_miniaturas, exist_ok=True)

        # Solo trae los registros donde la columna 'tipo' sea igual a 'video'
        videos = Video.query.filter_by(tipo='video').all()
        
        print(f"[+] Iniciando escaneo de miniaturas")

        for video in videos:
            # aqui comprueba si la primera miniatura de este video ya existe
            ruta_img1 = os.path.join(carpeta_miniaturas, f"{video.id}_1.jpg")
            if os.path.exists(ruta_img1):
                continue # Si ya existe, pos no intentamos crear mas miniaturas

            # Sacamos la duración exacta en segundos
            comando_duracion = [
                FFPROBE_CMD, '-v', 'error', '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', video.ruta_completa
            ]
            try:
                salida = subprocess.check_output(comando_duracion, text=True).strip()
                duracion = float(salida)
            except Exception as e:
                print(f"[!] Error leyendo duración de {video.ruta_completa}: {e}")
                continue

            momentos = [duracion * 0.1, duracion * 0.3, duracion * 0.5, duracion * 0.7, duracion * 0.9]
                
            print(f"[T] Extrayendo 5 miniaturas para: {video.ruta_completa.split('/')[-1]}")

            # Extraemos una imagen por cada marca de tiempo
            for i, tiempo in enumerate(momentos, start=1):
                ruta_salida = os.path.join(carpeta_miniaturas, f"{video.id}_{i}.jpg")
                
                # Comando de FFmpeg: Busca el segundo exacto (-ss), saca 1 frame (-vframes 1)
                # ajusta la calidad (-q:v 5) y lo escala a 320px de ancho (-vf scale=320:-1)
                comando_ffmpeg = [
                    FFMPEG_CMD, '-y', '-ss', str(tiempo), '-i', video.ruta_completa,
                    '-vframes', '1', '-q:v', '5', '-vf', 'scale=320:-1', ruta_salida
                ]
                subprocess.run(comando_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        print("-" * 50)
        print("Se han generado las nuevas miniaturas!")

# ----------------------------------------------------- EL BOTON DE GENERAR MINIATURAS MASIVAS
@config_bp.route('/generar_miniaturas_masivas', methods=['POST'])
def generar_miniaturas_masivas():
    
    # se crea un hilo independiente, le pasamos el contexto de la app y lo ejecuta
    hilo = threading.Thread(target=procesar_miniaturas_background, args=(current_app._get_current_object().app_context(),))
    hilo.start()
    
    # El servidor devuelve la respuesta al navegador INMEDIATAMENTE, sin esperar a que terminen los videos
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- ELIMINAR MINIATURAS
@config_bp.route('/borrar_miniaturas', methods=['POST'])
def borrar_miniaturas():
    from app import app
    import shutil
    
    carpeta_miniaturas = os.path.join(app.root_path, 'static', 'miniaturas')
    
    # Comprobamos que la carpeta exista antes de intentar borrarla
    if os.path.exists(carpeta_miniaturas):
        # 1. Eliminamos la carpeta y todo su contenido de un solo golpe
        shutil.rmtree(carpeta_miniaturas)
        # 2. La volvemos a crear vacía e intacta
        os.makedirs(carpeta_miniaturas, exist_ok=True)
        
    print("[!] Las miniaturas han sido borradas con exito.")
    
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- RECALCULAR DURACIONES FALLIDAS
@config_bp.route('/recalcular_duraciones', methods=['POST'])
def recalcular_duraciones():
    # Importacion interna
    from app import obtener_duracion_ffmpeg
    
    # Buscamos los que tengan la palabra "Video" en el campo de duracin
    videos_fallidos = Video.query.filter(Video.duracion == 'Video').all()
    cantidad_actualizada = 0
    
    for video in videos_fallidos:
        # calcular la duracion de nuevo
        nueva_duracion = obtener_duracion_ffmpeg(video.ruta_completa)
        
        # Si la funcion logra obtener una duracion real (distinta a "Video"):
        if nueva_duracion and nueva_duracion != 'Video':
            video.duracion = nueva_duracion
            cantidad_actualizada += 1
            
    db.session.commit()
    
    # comentario en la terminal del servidor
    print(f"[+] RECALCULO: Se repararon con éxito {cantidad_actualizada} duraciones de videos.")
    
    return redirect(url_for('config.panel'))

# -----------------------------------------------------------------------------CADDY
def actualizar_caddyfile():
    """Genera un Caddyfile dinámico con los discos duros y recarga el servidor web sin apagarlo"""
    from app import app
    import os, platform, subprocess
    from models import Ubicacion
    
    ubicaciones = Ubicacion.query.all()
    ruta_caddyfile = os.path.join(app.root_path, 'Caddyfile')
    
    with open(ruta_caddyfile, 'w', encoding='utf-8') as f:
        f.write("{\n")
        f.write(f"    admin localhost:{PUERTO_CADDY_ADMIN}\n")
        f.write("}\n\n")

        # 2. BLOQUE DEL SERVIDOR MULTIMEDIA
        f.write(f":{PUERTO_CADDY} {{\n")
        f.write("    # Archivos estaticos de Ghostube\n")
        f.write("    handle_path /static/* {\n")
        f.write("        root * \"static\"\n")
        f.write("        file_server\n")
        f.write("    }\n\n")
        
        f.write("    # Carpetas del Usuario\n")
        for ubi in ubicaciones:
            if os.path.exists(ubi.ruta):
                ruta_limpia = ubi.ruta.replace('\\', '/')
                f.write(f"    handle_path /disco_{ubi.id}/* {{\n")
                f.write(f"        root * \"{ruta_limpia}\"\n")
                f.write("        file_server\n")
                f.write("    }\n\n")
                
        f.write("    # Backend Flask\n")
        f.write(f"    reverse_proxy 127.0.0.1:{PUERTO_FLASK}\n")
        f.write("}\n")
    
    # Le deci a Caddy que lea el nuevo archivo de inmediato
    caddy_cmd = os.path.join(app.root_path, 'extenzzziones', 'caddy.exe') if platform.system() == 'Windows' else 'caddy'
    try:
        subprocess.run([caddy_cmd, 'reload', '--config', ruta_caddyfile], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[+] Configuracion de red Caddy actualizada y recargada con exito.")
    except Exception as e:
        pass