from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from models import db, Ubicacion, Tag, Video, Configuracion
import os
import platform
import subprocess
import threading
from flask import current_app

config_bp = Blueprint('config', __name__)

# CONTRASEÑA DEL MODO CONFIGURACION (Cámbiala aquí)
CONTRASENA_ADMIN = "1234"

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
        if password == CONTRASENA_ADMIN:
            session['admin_logged_in'] = True
            return redirect(url_for('config.panel'))
        else:
            return "Contraseña incorrecta <a href='/login'>Intentar de nuevo</a>"
    return render_template('login.html')

@config_bp.route('/panel')
def panel():
    # Protección: Si no está logueado, mandar al login
    if not session.get('admin_logged_in'):
        return redirect(url_for('config.login'))
    
    ubicaciones = Ubicacion.query.all()
    tags = Tag.query.all()
    config_modo = Configuracion.query.filter_by(clave='modo_miniaturas').first()
    modo_actual = config_modo.valor if config_modo else 'dinamico'

    return render_template('configuraciones.html', modo_actual=modo_actual, ubicaciones=ubicaciones, tags=tags)

@config_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('inicio'))

# ----------------------------------------------------- Configuraciones

# Gestión de Carpetas (Sobrenombres y Activar/Desactivar/Agregar)
@config_bp.route('/guardar_ubicaciones', methods=['POST'])
def guardar_ubicaciones():
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))

    # Agregar una nueva carpeta
    nueva_ruta = request.form.get('nueva_ruta')
    if nueva_ruta and os.path.exists(nueva_ruta):
        nombre_defecto = os.path.basename(nueva_ruta)
        nueva_ubi = Ubicacion(ruta=nueva_ruta, nombre=nombre_defecto)
        db.session.add(nueva_ubi)

    # Editar una carpeta existente
    ubicaciones = Ubicacion.query.all()
    for ubi in ubicaciones:
        # Actualizar nombre de la carpetasdfg
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

    db.session.commit()
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- LISTA NEGRA DE TAGS
@config_bp.route('/guardar_tags', methods=['POST'])
def guardar_tags():
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))
    
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
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))
    
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
# Esto sirve para eliminar de la base de datos los videos que ya no existen en el disco duro
# Cuando borras una carpeta completa, el server piensa que solo desconectaste una usb con esa carpeta, así que deja los datos de esos videos en la BDD
# Con esta funcion eliminas definitivamente todos los videos que no se encuentren en este momento, no importa si es por que la unidad de almacenamiento externa esta desconectada, elimina todo lo relacionado de la base de datos
# No voy a mejorar esto
@config_bp.route('/purgar_db', methods=['POST'])
def purgar_db():
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))
    
    # Buscamos videos que NO tienen ubicacion asignada -ubicacion_id es NULL-
    # Esto pasa cuando borraste la carpeta de la lista de configuraciones
    videos_huerfanos = Video.query.filter(Video.ubicacion_id == None).all()
    
    cantidad = len(videos_huerfanos)
    
    for video in videos_huerfanos:
        db.session.delete(video)
        
    db.session.commit()
    
    # Ejecutamos un VACUuM  para recuperar el espacio
    db.session.execute(db.text("VACUUM"))
    db.session.commit()
    
    print(f"--- PURGA COMPLETA: Se eliminaron {cantidad} videos de rutas inexistentes. ---")
    
    return redirect(url_for('config.panel'))

# ----------------------------------------------------- AUTOTAGGING POR CARPETAS
### Esta funcion funciona como un taggeador masivo, que le agregara las mismas etiquetas a todo el contenido multimedia de una carpeta

@config_bp.route('/detectar_carpetas', methods=['GET'])
def detectar_carpetas():
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))
    
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
            # Contamos cuantos archivos multimedia hay en ESTA carpeta (sin contar la subcarpetas dentro)
            cantidad = sum(1 for f in archivos if f.lower().endswith(ext_validas))
            
            if cantidad > 0:
                # Si la carpeta tiene multimedia valido, la agregamos a la lista
                lista_carpetas.append({
                    'ruta': raiz,
                    'cantidad': cantidad
                })
    
    # Ordenamos alfabéticamente para que sea fácil de leer
    lista_carpetas.sort(key=lambda x: x['ruta'])
    
    # Renderizamos la misma página pero enviándole esta lista nueva
    return render_template('configuraciones.html', 
                           ubicaciones=ubicaciones, # Necesario para la tabla de arriba
                           tags=Tag.query.all(),    # necesario para la lista negra
                           carpetas_detectadas=lista_carpetas) ### DATOS NUEVOS

# ----------------------------------------------------- AUTOTAGS MASIVOS
@config_bp.route('/aplicar_autotags', methods=['POST'])
def aplicar_autotags():
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))
    
    rutas = request.form.getlist('rutas_carpeta')
    nombres_tags_raw = request.form.getlist('nombres_tags')
    
    videos_afectados = 0
    tags_creados = 0
    
    for ruta, string_tags in zip(rutas, nombres_tags_raw):
        # Si el campo está vacío, pasamos a la siguiente carpeta
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
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))
    
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
        # se crea la carpeta si no existe
        from app import app, db, Video
        carpeta_miniaturas = os.path.join(app.root_path, 'static', 'miniaturas')
        os.makedirs(carpeta_miniaturas, exist_ok=True)

        videos = Video.query.all()
        print(f"[+] Iniciando escaneo de miniaturas para {len(videos)} videos...")

        for video in videos:
            # Comprobamos si la primera miniatura de este video ya existe (ej: 5_1.jpg)
            ruta_img1 = os.path.join(carpeta_miniaturas, f"{video.id}_1.jpg")
            if os.path.exists(ruta_img1):
                continue # Si ya existe, saltamos al siguiente video para ahorrar tiempo

            # Si no existe, usamos ffprobe para sacar la duración exacta en segundos
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

            ### if duracion < 5: 
                # Si es muy corto, tomamos solo 1 foto justo a la mitad
                momentos = [duracion * 0.5]
            ### else:
                # Si es normal, tomamos las 5 fotos
                momentos = [duracion * 0.1, duracion * 0.3, duracion * 0.5, duracion * 0.7, duracion * 0.9] 

            # Calculamos 5 marcas de tiempo: 10%, 30%, 50%, 70% y 90% del video
            momentos = [duracion * 0.1, duracion * 0.3, duracion * 0.5, duracion * 0.7, duracion * 0.9]
            print(f"🎬 Extrayendo 5 miniaturas para: {video.ruta_completa.split('/')[-1]}")

            # Extraemos una imagen por cada marca de tiempo
            for i, tiempo in enumerate(momentos, start=1):
                ruta_salida = os.path.join(carpeta_miniaturas, f"{video.id}_{i}.jpg")
                
                # Comando de FFmpeg: Busca el segundo exacto (-ss), saca 1 frame (-vframes 1)
                # ajusta la calidad (-q:v 5) y lo escala a 320px de ancho (-vf scale=320:-1)
                comando_ffmpeg = [
                    FFMPEG_CMD, '-y', '-ss', str(tiempo), '-i', video.ruta_completa,
                    '-vframes', '1', '-q:v', '5', '-vf', 'scale=320:-1', ruta_salida
                ]
                # Ejecutamos ocultando los textos largos de FFmpeg
                subprocess.run(comando_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[+] Los errores aparecen cuando intenta leer alguna imagen, es normal que pase.")
        print("-" * 50)
        print("Se han generado las nuevas miniaturas!")

# --- RUTA QUE ACTIVA EL BOTÓN ---
@config_bp.route('/generar_miniaturas_masivas', methods=['POST'])
def generar_miniaturas_masivas():
    if not session.get('admin_logged_in'): return redirect(url_for('config.login'))
    
    # Creamos un hilo independiente, le pasamos el contexto de la app y lo arrancamos
    hilo = threading.Thread(target=procesar_miniaturas_background, args=(current_app._get_current_object().app_context(),))
    hilo.start()
    
    # El servidor devuelve la respuesta al navegador INMEDIATAMENTE, sin esperar a que terminen los videos
    return redirect(url_for('config.panel'))