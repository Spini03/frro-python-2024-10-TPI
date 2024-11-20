from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import render_template, session
from flask_migrate import Migrate
from functools import wraps


app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_muy_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://soporte:s0p0rte123*@localhost/tpi_soporte'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos de base de datos

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
    paredes = db.relationship('Pared', backref='proyecto', lazy=True)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    precioPorUnidad = db.Column(db.Float, nullable=False)

class Pared(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    altura = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    id_material = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    material = db.relationship('Material', backref='paredes')
    mediciones = db.relationship('HistorialMediciones', backref='pared', lazy=True)

class HistorialMediciones(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fechaHora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    altura = db.Column(db.Float, nullable=False)
    ancho = db.Column(db.Float, nullable=False)
    costoTotal = db.Column(db.Float, nullable=False)
    id_pared = db.Column(db.Integer, db.ForeignKey('pared.id'), nullable=False)



# Funciones auxiliares

from flask_migrate import Migrate  
migrate = Migrate(app, db)         

def requiere_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))  # Redirecciona a login si no ha iniciado sesión
        return f(*args, **kwargs)
    return decorated_function

def medir_pared(image):
    # Aquí implementarías la lógica para medir la pared usando OpenCV
    # Este es un ejemplo simplificado, necesitarás desarrollar un algoritmo más robusto
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
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

# Rutas

@app.route('/')
@requiere_login
def home():
    proyectos = Proyecto.query.all()  # Mostrar todos los proyectos
    return render_template('home.html', proyectos=proyectos)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        mail = request.form['mail']
        password = request.form['password']

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
        flash('Credenciales inválidas')
    return render_template('login.html')

@app.route('/logout')
@requiere_login
def logout():
    session.pop('usuario_id', None)  # Elimina el ID del usuario de la sesión
    flash('Sesión cerrada.')
    return redirect(url_for('home'))

@app.route('/dashboard')
@requiere_login
def dashboard():
    proyectos = Proyecto.query.all()  # Mostrar todos los proyectos
    return render_template('dashboard.html', proyectos=proyectos)

@app.route('/proyecto/nuevo', methods=['GET', 'POST'])
@requiere_login
def nuevo_proyecto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nuevo_proyecto = Proyecto(nombre=nombre, id_usuario=1)  # Asumiendo un usuario por defecto
        db.session.add(nuevo_proyecto)
        db.session.commit()
        flash('Proyecto creado exitosamente')
        return redirect(url_for('dashboard'))
    return render_template('nuevo_proyecto.html')

@app.route('/proyecto/<int:proyecto_id>')
@requiere_login
def ver_proyecto(proyecto_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    return render_template('ver_proyecto.html', proyecto=proyecto)

@app.route('/pared/nueva/<int:proyecto_id>', methods=['GET', 'POST'])
@requiere_login
def nueva_pared(proyecto_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    if request.method == 'POST':
        file = request.files['image']
        id_material = request.form['material']
        
        image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_UNCHANGED)
        altura, ancho = medir_pared(image)
        
        nueva_pared = Pared(altura=altura, ancho=ancho, id_proyecto=proyecto_id, id_material=id_material)
        db.session.add(nueva_pared)
        db.session.commit()
        
        flash('Pared añadida exitosamente')
        return redirect(url_for('ver_proyecto', proyecto_id=proyecto_id))
    
    materiales = Material.query.all()
    return render_template('nueva_pared.html', proyecto_id=proyecto_id, materiales=materiales)

@app.route('/actualizar_precios')
@requiere_login
def actualizar_precios():
    precios = scrape_material_prices()
    for nombre, precio in precios.items():
        material = Material.query.filter_by(nombre=nombre).first()
        if material:
            material.precioPorUnidad = precio
    db.session.commit()
    flash('Precios de materiales actualizados')
    return redirect(url_for('dashboard'))

@app.route('/comparar_paredes', methods=['GET', 'POST'])
@requiere_login
def comparar_paredes():
    if request.method == 'POST':
        pared_ids = request.form.getlist('pared_ids')
        paredes = Pared.query.filter(Pared.id.in_(pared_ids)).all()
        
        comparacion = []
        for pared in paredes:
            costo = pared.altura * pared.ancho * pared.material.precioPorUnidad
            comparacion.append({
                'id': pared.id,
                'altura': pared.altura,
                'ancho': pared.ancho,
                'material': pared.material.nombre,
                'costo': costo
            })
        
        return render_template('resultados_comparacion.html', comparacion=comparacion)
    
    proyectos = Proyecto.query.all()  # Mostrar todos los proyectos
    return render_template('seleccionar_paredes.html', proyectos=proyectos)


if __name__ == '__main__':
    app.run(debug=True)