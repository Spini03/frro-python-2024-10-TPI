import base64
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import pymysql
from flask_sqlalchemy import SQLAlchemy
import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import render_template, session
from flask_migrate import Migrate
from functools import wraps

from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_muy_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://soporte:s0p0rte123*@127.0.0.1/tpi_soporte'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelos de base de datos
from models import Usuario, Proyecto, Pared, Material, HistorialMediciones

if __name__ == '__main__':
    app.run(debug=True)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    mail = db.Column(db.String(255), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False) 
    proyectos = db.relationship('Proyecto', backref='usuario', lazy=True)

class Proyecto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    paredes = db.relationship('Pared', backref='proyecto', lazy=True, cascade="all, delete")

class Material(db.Model):
    __tablename__ = 'material'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    precioPorUnidad = db.Column(db.Float, nullable=False)

class Pared(db.Model):
    __tablename__ = 'pared'

    id = db.Column(db.Integer, primary_key=True)
    altura = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    profundidad = db.Column(db.Float, nullable=False)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    id_material = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    material = db.relationship('Material', backref='paredes')
    mediciones = db.relationship('HistorialMediciones', backref='pared', lazy=True)

class HistorialMediciones(db.Model):
    __tablename__ = 'historial_mediciones'

    id = db.Column(db.Integer, primary_key=True)
    fechaHora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    altura = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    profundidad = db.Column(db.Float, nullable=False)  
    costoTotal = db.Column(db.Float, nullable=False)
    id_pared = db.Column(db.Integer, db.ForeignKey('pared.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    material = db.relationship('Material', backref='mediciones')

# Funciones auxiliares

#from flask_migrate import Migrate  
#migrate = Migrate(app, db)         

def requiere_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))  # Redirecciona a login si no ha iniciado sesión
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/test_delete/<int:proyecto_id>')
def test_delete(proyecto_id):
    proyecto = Proyecto.query.get(proyecto_id)
    if not proyecto:
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('dashboard'))
    try:
        db.session.delete(proyecto)
        db.session.commit()
        return "Proyecto eliminado exitosamente"
    except Exception as e:
        return f"Error eliminando proyecto: {e}"
    return redirect(url_for('dashboard'))

def medir_pared(image):
    # Aquí implementarías la lógica para medir la pared usando OpenCV
    # Este es un ejemplo simplificado, necesitarás desarrollar un algoritmo más robusto
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 10, 50, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
    
    # Aquí procesarías las líneas para determinar altura y ancho
    # Por ahora, devolvemos valores de ejemplo
    return 3.0, 5.0  # altura, ancho

def scrape_material_prices():
    url = "https://www.ejemplo-materiales-construccion.com/precios"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    precios = {}
    for item in soup.find_all('div', class_='material-item'):
        nombre = item.find('span', class_='nombre').text
        precio = float(item.find('span', class_='precio').text.replace('$', ''))
        precios[nombre] = precio

    return precios

def actualizar_precios_materiales():
    # Ejemplo de scraping de precios
    urls = {
        'ladrillos': 'https://ejemplo.com/precios-ladrillos',
        'cemento': 'https://ejemplo.com/precios-cemento',
        # etc
    }
    
    for material_tipo, url in urls.items():
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            precio = soup.find('span', class_='precio').text
            
            material = Material.query.filter_by(nombre=material_tipo).first()
            if material:
                material.precioPorUnidad = float(precio)
                db.session.commit()
        except Exception as e:
            print(f"Error actualizando precio de {material_tipo}: {str(e)}")


def calibrate_camera(image, known_width_meters, known_width_pixels):
    # Calcula la relación entre píxeles y metros
    pixel_to_meter_ratio = known_width_meters / known_width_pixels
    return pixel_to_meter_ratio

def draw_contours(image, contours):
    # Dibujar contornos en la imagen
    image_with_contours = cv2.drawContours(image.copy(), contours, -1, (0, 255, 0), 2)
    return image_with_contours

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

# Rutas

@app.route('/')
@requiere_login
def home():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))  # Si está autenticado, redirige al dashboard
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        mail = request.form['mail']
        password = request.form['password']

        if not nombre or not mail or not password:
            flash('Todos los campos son obligatorios')
            return redirect(url_for('registro'))

        usuario_existente = Usuario.query.filter_by(mail=mail).first()
        if usuario_existente:
            flash('El correo electrónico ya está registrado')
            return redirect(url_for('registro'))

        nuevo_usuario = Usuario(nombre=nombre, mail=mail, contraseña=password) 

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Registro exitoso.')
        return redirect(url_for('login'))

    return render_template('registro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mail = request.form['mail']
        password = request.form['password']

        usuario = Usuario.query.filter_by(mail=mail).first()
        if usuario and usuario.contraseña == password:
            session['usuario_id'] = usuario.id  # Guarda el ID del usuario en la sesión
            flash('Inicio de sesión exitoso.')
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
@requiere_login
def logout():
    session.pop('usuario_id', None)  # Elimina el ID del usuario de la sesión
    flash('Has cerrado sesión correctamente.')
    return redirect(url_for('login'))

@app.route('/dashboard')
@requiere_login
def dashboard():
     if 'usuario_id' not in session:
        print("El usuario no está autenticado.")
        return redirect(url_for('login'))  # Redirige al login si no está autenticado
     else:
        proyectos = Proyecto.query.filter_by(id_usuario=session['usuario_id']).all()
        return render_template('dashboard.html', proyectos=proyectos)

@app.route('/proyecto/<int:proyecto_id>/eliminar', methods=['POST'])
@requiere_login
def eliminar_proyecto(proyecto_id):
    print(f"Solicitud POST recibida para eliminar proyecto con ID: {proyecto_id}")
    proyecto = Proyecto.query.get_or_404(proyecto_id)

    if 'usuario_id' not in session:
        print("El usuario no está autenticado.")
        return redirect(url_for('login'))

    if proyecto.id_usuario != session['usuario_id']:
        print(f"Usuario {session['usuario_id']} no tiene permiso para eliminar proyecto {proyecto_id}")
        flash('No tienes permiso para eliminar este proyecto.')
        return redirect(url_for('dashboard'))

    try:
        db.session.delete(proyecto)
        db.session.commit()
        flash('Proyecto eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar proyecto: {e}")  # Para depurar el error
        flash('Error al eliminar el proyecto: ' + str(e))

    return redirect(url_for('dashboard'))

@app.route('/nuevo_proyecto', methods=['GET', 'POST'])
@requiere_login
def nuevo_proyecto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        usuario_id = session.get('usuario_id')
        
        nuevo_proyecto = Proyecto(
            nombre=nombre,
            id_usuario=usuario_id
        )
        
        try:
            db.session.add(nuevo_proyecto)
            db.session.commit()
            flash('Proyecto creado exitosamente')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear el proyecto: ' + str(e))
            return redirect(url_for('nuevo_proyecto'))
            
    return render_template('nuevo_proyecto.html')


@app.route('/proyecto/<int:proyecto_id>')
@requiere_login
def ver_proyecto(proyecto_id):
    proyecto = Proyecto.query.options(
        joinedload(Proyecto.paredes).joinedload(Pared.mediciones)
    ).get_or_404(proyecto_id)

    materiales = Material.query.all()
    
    # Obtener las mediciones asociadas a las paredes del proyecto
    mediciones = []
    for pared in proyecto.paredes:
        mediciones.extend(pared.mediciones)
    print(mediciones)
    return render_template('proyecto_detalle.html', proyecto=proyecto, materiales=materiales, mediciones=mediciones)

@app.route('/guardar_mediciones/<int:proyecto_id>', methods=['POST'])
@requiere_login
def guardar_mediciones(proyecto_id):
   
    # Lógica para guardar mediciones asociadas al proyecto
    Proyecto.query.get_or_404(proyecto_id)
    # (Implementa aquí la lógica específica para guardar las mediciones)
    return redirect(url_for('ver_proyecto', proyecto_id=proyecto_id))

# Otros métodos se omiten para mantener el código más limpio y conciso

