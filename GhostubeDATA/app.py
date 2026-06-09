import os
import json
import subprocess 
import platform
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

# ---------------------------------------------- CONFIGURACIÓN DE EXTENSIONES 
EXT_VIDEO = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
EXT_IMAGEN = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

# ---------------------------------------------- Ver si esto es linu o windo
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if platform.system() == 'Windows':
    FFPROBE_CMD = os.path.join(BASE_DIR, 'extenzzziones', 'ffprobe.exe')
else:
    FFPROBE_CMD = 'ffprobe'


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
        #cambialo por lo que quieras
        return "v:deo" 

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
                        duracion_str = "--:--" #cambialo por lo que quieras
                        
                        # Solo calculamos duracion si es un video
                        if es_video:
                            duracion_str = obtener_duracion_ffmpeg(ruta_abs)
                        
                        nuevo_media = Video(
                            titulo=titulo_limpio, 
                            archivo=archivo, 
                            ruta_completa=ruta_abs, 
                            ubicacion_id=ubicacion.id,
                            duracion=duracion_str,
                            tipo=tipo_archivo ### Guardamos el tipo de archivo (video o imagen
                        )
                        db.session.add(nuevo_media)
                        print(f" [+] Nuevo {tipo_archivo}: {titulo_limpio}")

    # --- LIMPIEZA INTELIGENTE DE VIDEOS QUE FALTAN AL ENCENDER EL SERVER
    media_db = Video.query.all()
    for item in media_db:
        # 1- Verificamos si este video tiene una ubicación asignada
        if item.ubicacion:
            # 2- El disco duro o carpeta raíz esta presente?
            if not os.path.exists(item.ubicacion.ruta):
                # 2.1- No está? Pues no lo borramos, puede que lo vuelvas a conectar despues.
                continue 
        
        # 3. Si el disco SI está conectado, pero el archivo no está,
        # entonces el usuario borró el video intencionalmente. Ahora si lo borramos de la Base de Datos.
        if not os.path.exists(item.ruta_completa):
            db.session.delete(item)
            print(f" [-] Archivo eliminado del disco, borrando de DB: {item.titulo}")
            
    db.session.commit()


# ---------------------------------------------- FUNCIÓN AYUDANTE PARA BUSQUEDA Y ORDENAMIENTO
def construir_query_busqueda(busqueda, modo_busqueda, modo_vis, orden):
    query = Video.query.join(Ubicacion).filter(Ubicacion.activa == True)
    
    if modo_vis == 'videos': query = query.filter(Video.tipo == 'video')
    elif modo_vis == 'imagenes': query = query.filter(Video.tipo == 'imagen')

    if not busqueda:
        ids_ocultos = db.session.query(Video.id).join(Video.tags).filter(Tag.oculto == True)
        query = query.filter(Video.id.notin_(ids_ocultos))
    else:
        try:
            import json
            datos_tagify = json.loads(busqueda)
            terminos = [item['value'] for item in datos_tagify]
        except:
            terminos = busqueda.split()
        
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

    # --- LOGICA DE ORDENAMIENTO
    if orden == 'alfabetico':
        query = query.order_by(Video.titulo.asc())
    else:
        query = query.order_by(Video.id.desc()) # Por defecto: Más recientes primero
        
    return query




# ---------------------------------------------> RUTAS <---

@app.route('/cambiar_modo')
def cambiar_modo():
    # Atrapamos lo que el usuario eligió en el nuevo desplegable
    modo_elegido = request.args.get('modo_visualizacion')
    
    if modo_elegido in ['videos', 'imagenes', 'todos']:
        session['modo_visualizacion'] = modo_elegido
        
    return redirect(url_for('inicio'))
# ---------------------------------------------- PAGINA: PRINCIPAL
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
    
    # Usamos la función ayudante
    query = construir_query_busqueda(busqueda, modo_busqueda, modo_vis, orden)
    
    # eN per_page=50 puedes cambiar cuántos resultados quieres por página
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
    
    # Recuperamos el contexto de cómo llegó el usuario aquí (se recupera desde el link)
    # Se usa para hacer la "playlist" y así saber qué videos van antes y después del actual
    q = request.args.get('q', '')
    modo_busqueda = request.args.get('modo_busqueda', 'and')
    orden = request.args.get('orden', 'id_desc')
    modo_vis = session.get('modo_visualizacion', 'videos')
    
    # 2. Reconstruimos la "Playlist" virtual (solo sac los IDs y hace que la url se vea fea)
    query_playlist = construir_query_busqueda(q, modo_busqueda, modo_vis, orden)
    resultados = query_playlist.with_entities(Video.id).all()
    lista_ids = [r[0] for r in resultados]
    
    # 3. Averiguamos quién está antes y quién después
    prev_id, next_id = None, None
    if id_video in lista_ids:
        indice = lista_ids.index(id_video)
        if indice > 0: prev_id = lista_ids[indice - 1]
        if indice < len(lista_ids) - 1: next_id = lista_ids[indice + 1]

    # Pasamos todo esto a la plantilla
    return render_template('ver_video.html', video=video, prev_id=prev_id, next_id=next_id, q=q, modo_busqueda=modo_busqueda, orden=orden)


# ---------------------------------------------- HTML de "ABOUT GHOSTUBE"
@app.route('/boutm')
def informacion():
    return render_template('boutm.html')


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
    directorio = os.path.dirname(video.ruta_completa)
    nombre_archivo = os.path.basename(video.ruta_completa)
    return send_from_directory(directorio, nombre_archivo)


# ---------------------------------------------- Gracias por descargar este pequeño proyecto hecho con más fé que conocimiento
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # --- configuraciones por defecto para la tabla miniaturas
        config_miniaturas = Configuracion.query.filter_by(clave='modo_miniaturas').first()
        if not config_miniaturas:
            config_inicial = Configuracion(clave='modo_miniaturas', valor='dinamico')
            db.session.add(config_inicial)
            db.session.commit()
    app.run(debug=True, port=5000, host='0.0.0.0')