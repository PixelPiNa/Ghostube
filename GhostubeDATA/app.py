import os
import json
import subprocess 
import platform
import socket
import math       
from flask import Flask, render_template, send_from_directory, request, redirect, url_for, jsonify, session
from sqlalchemy import or_

from models import Configuracion, db, Video, Tag, Ubicacion
from configuraciones import config_bp

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cine.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)
#app.secret_key = 'puedes_poner_una_contrasena_de_cookie_personalizada_aqui_SoloSiSabesLoQueHaces' 

db.init_app(app)
app.register_blueprint(config_bp)

# --- CONFIGURACION DE RED ---
PUERTO_CADDY = 9090
PUERTO_FLASK = 9091
PUERTO_CADDY_ADMIN = 2019
# --- FIN CONFIGURACION ---

# ---------------------------------------------- CONFIGURACIÓN DE EXTENSIONES 
EXT_VIDEO = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
EXT_IMAGEN = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

# ---------------------------------------------- Ver si esto es linu o windo
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if platform.system() == 'Windows':
    FFPROBE_CMD = os.path.join(BASE_DIR, 'extenzzziones', 'ffprobe.exe')
else:
    FFPROBE_CMD = 'ffprobe'

# ---------------------------------------------- Ver IP
def obtener_ip_local():
    """Obtiene la IP local real de la máquina dentro de la red Wi-Fi/LAN"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# Esta funcion utiliza ffmpeg, una herramienta preinstalada en algunas distros de linux
def obtener_duracion_ffmpeg(ruta_archivo):
    """Calcula duración solo si es video."""
    try:
        comando = [FFPROBE_CMD, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', ruta_archivo]
        resultado = subprocess.check_output(comando).decode('utf-8').strip()
        segundos_total = float(resultado)
        horas = math.floor(segundos_total / 3600)
        minutos = math.floor((segundos_total % 3600) / 60)
        segundos = math.floor(segundos_total % 60)
        if horas > 0: return f"{horas}:{minutos:02d}:{segundos:02d}"
        else: return f"{minutos}:{segundos:02d}"
    except: 
        # Si no tienes ffmpeg instalado o algo falla, no te preocupes, solo devuelve lo de abajo
        return "Video" 

# ---------------------------------------------- ESCANEO de Videos e Imagenes
def escanear_multimedia():
    ubicaciones = Ubicacion.query.filter_by(activa=True).all()
    
    for ubicacion in ubicaciones:
        if not os.path.exists(ubicacion.ruta): continue
            
        for raiz, carpetas, archivos in os.walk(ubicacion.ruta):
            for archivo in archivos:
                archivo_low = archivo.lower()
                ruta_abs = os.path.join(raiz, archivo)
                
                # Determinamos tipo
                es_video = archivo_low.endswith(EXT_VIDEO)
                es_imagen = archivo_low.endswith(EXT_IMAGEN)
                
                if es_video or es_imagen:
                    tipo_archivo = 'video' if es_video else 'imagen'
                    
                    video_existente = Video.query.filter_by(ruta_completa=ruta_abs).first()
                    
                    if not video_existente:
                        titulo_limpio = os.path.splitext(archivo)[0]
                        duracion_str = "1" # Este 1 se va a registrar en la "duracion" de una imagen
                        
                        # Solo calculamos duracion si es un video
                        if es_video:
                            duracion_str = obtener_duracion_ffmpeg(ruta_abs)
                        
                        nuevo_media = Video(
                            titulo=titulo_limpio, # le quita la extencion
                            archivo=archivo, # el nombre exacto del archivo: archivo_entupc.mp4
                            ruta_completa=ruta_abs, # La ruta absoluta del archivo
                            ubicacion_id=ubicacion.id, # el id de la ruta absoluta registrada
                            duracion=duracion_str, # puede guardar: "Video", "1" o "00:00"
                            tipo=tipo_archivo # video o imagen
                        )
                        db.session.add(nuevo_media)
                        print(f" [+] Nuevo {tipo_archivo}: {titulo_limpio}")

    # ------------------- LIMPIEZA INTELIGENTE DE VIDEOS QUE FALTAN AL ENCENDER EL SERVER
    media_db = Video.query.all()
    for item in media_db:
        # este video tiene una ubicación asignada?
        if item.ubicacion:
            # El disco duro o carpeta raíz esta presente?
            if not os.path.exists(item.ubicacion.ruta):
                # No está la carpeta completa? Pues no borramos los videos, puede que vuelvas a conectar la unidad despues.
                continue 
        
        # el disco SI está conectado, pero el archivo no está?
        # entonces el usuario borró el video intencionalmente. Ahora si lo borramos de la Base de Datos.
        if not os.path.exists(item.ruta_completa):
            db.session.delete(item)
            print(f" [-] Archivo eliminado del disco, borrando de DB: {item.titulo}")
            
    db.session.commit()

    # --- MINIATURAS ---
    # Se lee la configuración de la base de datos
    config_miniaturas = Configuracion.query.filter_by(clave='modo_miniaturas').first()
    
    # si la configuracion de modo es = estatico
    if config_miniaturas and config_miniaturas.valor == 'estatico':
        import threading
        # Importación local para evitar bucles de importación con configuraciones.py
        from configuraciones import procesar_miniaturas_background
        
        print("[T] Buscando nuevos videos para generar miniaturas...")
        
        # Lanzamos el proceso sin detener el flujo principal de la app
        hilo_miniaturas = threading.Thread(target=procesar_miniaturas_background, args=(app.app_context(),))
        hilo_miniaturas.start()


# ---------------------------------------------- FUNCIÓN DE PLAYLIST (para poder avanzar y retroceder en los videos que buscaste y como los decidiste ordenar)
def construir_query_busqueda(busqueda, modo_busqueda, modo_vis, orden):
    query = Video.query.join(Ubicacion).filter(Ubicacion.activa == True)
    
    if modo_vis == 'videos': query = query.filter(Video.tipo == 'video')
    elif modo_vis == 'imagenes': query = query.filter(Video.tipo == 'imagen')

    # Procesar los tags primero
    terminos = []
    if busqueda:
        try:
            import json
            datos_tagify = json.loads(busqueda)
            terminos = [item['value'] for item in datos_tagify]
        except:
            terminos = busqueda.split()

    # Revisamos si el usuario está ingresando un tag oculto en el buscador
    tag_oculto_buscado = None
    for termino in terminos:
        # Buscamos si algun tag introducido corresponde a un tag de la lista negra
        tag_db = Tag.query.filter(Tag.nombre.ilike(termino), Tag.oculto == True).first()
        if tag_db:
            tag_oculto_buscado = tag_db #Se encontró el tag de la lista negra
            break 

    # Aplicamos el filtro de ocultar contenido
    config_sensible = Configuracion.query.filter_by(clave='ocultar_sensible').first()
    if config_sensible and config_sensible.valor == 'True':
        if tag_oculto_buscado:
            # Si se buscó el tag exacto, se muestran los videos con el tag
            query = query.filter(or_(
                ~Video.tags.any(Tag.oculto == True),
                Video.tags.contains(tag_oculto_buscado)
            ))
        else:
            # Si no se busco el tag oculto, no se muestra nada que lo contenga
            query = query.filter(~Video.tags.any(Tag.oculto == True))

    # Continuamos buscando tags normalmente
    if terminos:
        if modo_busqueda == 'and':
            for termino in terminos:
                query = query.filter(or_(Video.titulo.ilike(f'%{termino}%'), Video.tags.any(Tag.nombre.ilike(f'%{termino}%'))))
        else:
            condiciones = []
            for termino in terminos:
                condiciones.append(Video.titulo.ilike(f'%{termino}%'))
                condiciones.append(Video.tags.any(Tag.nombre.ilike(f'%{termino}%')))
            query = query.filter(or_(*condiciones))
        query = query.distinct()

    # aqui se ordenan las cosas
    if orden == 'alfabetico':
        query = query.order_by(Video.titulo.asc())
    else:
        query = query.order_by(Video.id.desc())
        
    return query

# ------------------------------------ GUARDIAN
@app.before_request
def guardian_de_seguridad():
    # Evitar errores si la ruta no existe
    if not request.endpoint:
        return
        
    # 1 Rutas que siempre deben estar libres
    rutas_libres = ['static', 'config.login']
    if request.endpoint in rutas_libres:
        return

    # 2 Si el usuario ya metió la clave, tiene acceso a todo, lo dejamos pasar
    if session.get('admin_logged_in'):
        return

    # 3 Leer qué bloqueos están activos en la BD
    configs = {c.clave: c.valor for c in Configuracion.query.all()}
    b_general = configs.get('bloqueo_general') == 'True'
    b_explorar = configs.get('bloqueo_explorar') == 'True'
    b_config = configs.get('bloqueo_configuraciones') == 'True'
    b_sensible = configs.get('ocultar_sensible') == 'True'

    # 4 Aplicar bloqueo a los videos en general
    if request.endpoint == 'stream_video':
        if b_general and not session.get('admin_logged_in'):
            return "Acceso denegado", 403
        
    if b_general:
        session['next_url'] = request.url # Guardamos la URL intentada
        return redirect(url_for('config.login'))

    if b_explorar and request.endpoint == 'explorar_tags': 
        session['next_url'] = request.url
        return redirect(url_for('config.login'))

    if b_config and request.endpoint.startswith('config.'):
        session['next_url'] = request.url
        return redirect(url_for('config.login'))

    # 5 Bloqueo de tags ocultos
    if b_sensible:
        q = request.args.get('q')
        if q:
            try:
                import json
                datos_tagify = json.loads(q)
                terminos = [item['value'] for item in datos_tagify]
            except:
                terminos = q.split() 
            
            for termino in terminos:
                tag_prohibido = Tag.query.filter(Tag.nombre.ilike(termino), Tag.oculto == True).first()
                if tag_prohibido:
                    if not session.get('admin_logged_in'):
                        session['next_url'] = request.url # Guardamos la búsqueda para completarla luego del login
                        return redirect(url_for('config.login'))


# ---------------------------------------------> RUTAS <---

@app.route('/cambiar_modo')
def cambiar_modo():
    # Lo que diga el menu desplegable se recibe aqui
    modo_elegido = request.args.get('modo_visualizacion')
    
    if modo_elegido in ['videos', 'imagenes', 'todos']:
        session['modo_visualizacion'] = modo_elegido
        
    return redirect(url_for('inicio'))

# ---------------------------------------------- PRINCIPAL
@app.route('/', methods=['GET'])
def inicio():
    page = request.args.get('page', 1, type=int)
    if page == 1: escanear_multimedia()
    
    busqueda = request.args.get('q', '')
    modo_busqueda = request.args.get('modo_busqueda', 'and') 
    modo_vis = session.get('modo_visualizacion', 'videos')
    orden = request.args.get('orden', 'id_desc')
    config_modo = Configuracion.query.filter_by(clave='modo_miniaturas').first()
    modo_actual = config_modo.valor if config_modo else 'dinamico'
    
    # Usamos la funcion playlists
    query = construir_query_busqueda(busqueda, modo_busqueda, modo_vis, orden)
    
    # eN per_page=50 puedes cambiar cuantos resultados quieres por pagina
    paginacion = query.paginate(page=page, per_page=50, error_out=False)
    todos_los_tags = Tag.query.filter_by(oculto=False).all()
    
    return render_template('index.html', modo_miniaturas=modo_actual, paginacion=paginacion, busqueda=busqueda, todos_los_tags=todos_los_tags, modo=modo_vis, modo_busqueda=modo_busqueda, orden=orden)
    
# Hola adrian

# ---------------------------------------------- PAGINA: RUTA PARA LA PÁGINA DE EXPLORACIÓN DE TAGS
@app.route('/explorar')
def explorar_tags():
    # Consultamos la base de datos y Traemos todos los tags que no esten en la lista negra (oculto=False)
    # y los ordenamos alfabéticamente por su nombre.
    tags_visibles = Tag.query.filter_by(oculto=False).order_by(Tag.nombre.asc()).all()
    
    # Enviamos la lista creada a la plantilla explorar.html
    return render_template('explorar.html', tags=tags_visibles)


@app.route('/api/tags')
def api_tags():
    tags = Tag.query.filter_by(oculto=False).with_entities(Tag.nombre).all()
    return jsonify([t[0] for t in tags])


# ---------------------------------------------- PAGINA: AQUI SE RENDERIZA EL HTML DE VER VIDEO 
@app.route('/video/<int:id_video>')
def ver_video(id_video):
    video = Video.query.get_or_404(id_video)
    
    # Recuperamos el contexto de cómo llegó el usuario aquí (se recupera desde la url)
    # Se usa para hacer la "playlist" y así saber qué videos van antes y después del video presentado
    q = request.args.get('q', '')
    modo_busqueda = request.args.get('modo_busqueda', 'and')
    orden = request.args.get('orden', 'id_desc')
    modo_vis = session.get('modo_visualizacion', 'videos')
    
    # Reconstruimos la "playlist" virtual 
    query_playlist = construir_query_busqueda(q, modo_busqueda, modo_vis, orden)
    resultados = query_playlist.with_entities(Video.id).all()
    lista_ids = [r[0] for r in resultados]
    
    # Averiguamos quien esta antes y quién despues
    prev_id, next_id = None, None
    if id_video in lista_ids:
        indice = lista_ids.index(id_video)
        if indice > 0: prev_id = lista_ids[indice - 1]
        if indice < len(lista_ids) - 1: next_id = lista_ids[indice + 1]

    # Pasamos todo esto al html
    return render_template('ver_video.html', video=video, prev_id=prev_id, next_id=next_id, q=q, modo_busqueda=modo_busqueda, orden=orden)


# ---------------------------------------------- HTML de "ABOUT GHOSTUBE"
@app.route('/boutm')
def informacion():
    return render_template('boutm.html')
# ---------------------------------------------- HTML de "IP"
@app.route('/ghostube')
def holamundo():
    ip_red = obtener_ip_local()
    # 2. Le pegamos el puerto 9090 (El puerto de alta velocidad de Caddy)
    direccion_publica = f"http://{ip_red}:{PUERTO_CADDY}"
    
    return render_template('ip.html',direccion_publica=direccion_publica)


# ---------------------------------------------- HERRAMIENTA: GUARDAR CAMBIOS DE UN VIDEO (TITULO Y TAGS)
@app.route('/guardar/<int:id_video>', methods=['POST'])
def guardar_cambios(id_video):
    video = Video.query.get_or_404(id_video)
    nuevo_titulo = request.form.get('titulo')
    if nuevo_titulo: video.titulo = nuevo_titulo
    tags_texto = request.form.get('tags') 
    video.tags = []
    if tags_texto:
        nombres_tags = []
        try:
            datos_json = json.loads(tags_texto)
            nombres_tags = [item['value'] for item in datos_json]
        except (json.JSONDecodeError, TypeError):
            nombres_tags = [t.strip() for t in tags_texto.split(',')]
        for nombre in nombres_tags:
            if not nombre: continue 
            tag_db = Tag.query.filter_by(nombre=nombre).first()
            if not tag_db:
                tag_db = Tag(nombre=nombre)
                db.session.add(tag_db)
            if tag_db not in video.tags:
                video.tags.append(tag_db)
    db.session.commit()
    return redirect(url_for('ver_video', id_video=id_video))

# ----------------------------------------------------- para que era esto?
@app.route('/stream/<int:id_video>')
def stream_video(id_video):
    video = Video.query.get_or_404(id_video)
    
    # Por seguridad, si la carpeta desaparecio
    if not video.ubicacion:
        return "Ubicación desconectada", 404
        
    ruta_relativa = os.path.relpath(video.ruta_completa, video.ubicacion.ruta)
    ruta_relativa = ruta_relativa.replace('\\', '/') # Convertimos a formato web
    
    from urllib.parse import quote
    # El navegador pide este link a Caddy sin que el usuario lo note
    url_caddy = f"/disco_{video.ubicacion_id}/{quote(ruta_relativa)}"
    
    return redirect(url_caddy)


# ---------------------------------------------- Gracias por descargar este pequeño proyecto hecho con más fé que conocimiento
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Lista de ajustes predeterminados (solo se ejecuta la primera vez que abres el server)
        ajustes_defecto = {
            'modo_miniaturas': 'dinamico',
            'pass_maestra': '',             
            'bloqueo_general': 'False',
            'bloqueo_explorar': 'False',    
            'bloqueo_configuraciones': 'False',
            'ocultar_sensible': 'False'
        }
        
        for clave, valor in ajustes_defecto.items():
            if not Configuracion.query.filter_by(clave=clave).first():
                nueva_config = Configuracion(clave=clave, valor=valor)
                db.session.add(nueva_config)
                
        db.session.commit()
    app.run(debug=False, port=PUERTO_FLASK, host='127.0.0.1')