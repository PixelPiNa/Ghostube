from flask_sqlalchemy import SQLAlchemy

# Inicializamos la DB aquí
db = SQLAlchemy()

# ---------------------------------------------- TABLAS

class Ubicacion(db.Model): # es la carpeta, el lugar donde se deben buscar los videos
    id = db.Column(db.Integer, primary_key=True)
    ruta = db.Column(db.String(500), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False) 
    activa = db.Column(db.Boolean, default=True) 
    
    # Campo de color (Rojo por defecto)
    color = db.Column(db.String(20), default='#ff5252')

    def __repr__(self):
        return f'<Ubicacion {self.nombre}>'

class Video(db.Model): # es el video en sí, con su título, ruta, duración y asi
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    archivo = db.Column(db.String(300), nullable=False)
    ruta_completa = db.Column(db.String(500), unique=True, nullable=False)
    
    duracion = db.Column(db.String(20), default="--:--")
    
    # hay nuevo campo? video o imagen
    tipo = db.Column(db.String(10), default='video') 
    
    ubicacion_id = db.Column(db.Integer, db.ForeignKey('ubicacion.id'), nullable=True)
    ubicacion = db.relationship('Ubicacion', backref=db.backref('videos', lazy=True, cascade="all, delete-orphan"))
    tags = db.relationship('Tag', secondary='video_tags', backref=db.backref('videos', lazy=True))

class Tag(db.Model): #etiquetas
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    oculto = db.Column(db.Boolean, default=False) 

# Tabla intermedia que ya ni me acuerdo pa que sirve, pero parece importante
video_tags = db.Table('video_tags',
    db.Column('video_id', db.Integer, db.ForeignKey('video.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Configuracion(db.Model): #otras cosas
    __tablename__ = 'configuracion'
    clave = db.Column(db.String(50), primary_key=True)
    valor = db.Column(db.String(255), nullable=False)