from flask_sqlalchemy import SQLAlchemy

# No importes db aquí al principio, lo haremos después
db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    mail = db.Column(db.String(255), nullable=False, unique=True)
    contraseña = db.Column(db.String(255), nullable=False)

class Proyecto(db.Model):
    __tablename__ = 'proyecto'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class Pared(db.Model):
    __tablename__ = 'pared'
    id = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    id_material = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    altura = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    profundidad = db.Column(db.Float, nullable=False)

class Material(db.Model):
    __tablename__ = 'material'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    precioPorUnidad = db.Column(db.Float, nullable=False)

class HistorialMediciones(db.Model):
    __tablename__ = 'historial_mediciones'
    id = db.Column(db.Integer, primary_key=True)
    fechaHora = db.Column(db.DateTime, nullable=False)
    altura = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    profundidad = db.Column(db.Float, nullable=False)
    costoTotal = db.Column(db.Float, nullable=False)
    id_pared = db.Column(db.Integer, db.ForeignKey('pared.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)

# Ahora importamos db solo después de que la aplicación haya sido configurada
from app import db
