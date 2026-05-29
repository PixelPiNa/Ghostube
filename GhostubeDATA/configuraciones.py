from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Ubicacion, Tag, Video
import os

config_bp = Blueprint('config', __name__)

# CONTRASEÑA SIMPLE (Cámbiala aquí)
CONTRASENA_ADMIN = "25320740"


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
    return render_template('configuraciones.html', ubicaciones=ubicaciones, tags=tags)

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