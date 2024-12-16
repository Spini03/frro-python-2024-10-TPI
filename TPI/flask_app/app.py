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
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://soporte:s0p0rte123*@localhost/tpi_soporte'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


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
        joinedload(Proyecto.paredes).joinedload(Pared.mediciones).joinedload(HistorialMediciones.material)
    ).get_or_404(proyecto_id)

    # Obtener las mediciones directamente con sus materiales ya cargados
    mediciones = [medicion for pared in proyecto.paredes for medicion in pared.mediciones]
    
    materiales = Material.query.all()
    
    return render_template('proyecto_detalle.html', 
                           proyecto=proyecto, 
                           materiales=materiales, 
                           mediciones=mediciones)

@app.route('/proyecto/<int:proyecto_id>/guardar_mediciones', methods=['POST'])
@requiere_login
def guardar_mediciones(proyecto_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    print(request.form)  # Imprime los datos del formulario en la consola
    
    try:
        ancho = float(request.form['ancho'])
        alto = float(request.form['alto'])
        profundidad = float(request.form['profundidad'])
        material_id = int(request.form['material'])
        
        material = Material.query.get_or_404(material_id)
        
        # Crear una nueva pared
        nueva_pared = Pared(
            altura=alto,
            ancho=ancho,
            profundidad=profundidad,  # Asegúrate de que este campo exista en la tabla Pared
            id_proyecto=proyecto_id,
            id_material=material_id
        )
        
        db.session.add(nueva_pared)
        db.session.flush()  # Flush para obtener el ID de la nueva pared
        
        # Calcular costo total
        area_total = 2 * (ancho * alto + ancho * profundidad + alto * profundidad)  # Área total de la pared
        costo_total = area_total * material.precioPorUnidad
        
        # Crear una nueva medición asociada a la nueva pared
        nueva_medicion = HistorialMediciones(
            altura=alto,
            ancho=ancho,
            profundidad=profundidad,
            costoTotal=costo_total,
            id_pared=nueva_pared.id,
            material_id=material_id
        )
        
        db.session.add(nueva_medicion)
        db.session.commit()
        flash('Mediciones guardadas exitosamente')
    except Exception as e:
        db.session.rollback()
        flash('Error al guardar las mediciones: ' + str(e))
    
    print("Redirigiendo a ver_proyecto")  # Imprime un mensaje en la consola
    return redirect(url_for('ver_proyecto', proyecto_id=proyecto_id))


@app.route('/proyecto/<int:proyecto_id>/process_reference', methods=['POST'])
def process_reference(proyecto_id):
    try:
        data = request.json
        image_data = data['imageData']
        # Decodificar la imagen recibida
        encoded_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Convertir a escala de grises y detectar bordes
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 10, 50)
        # Detectar contornos
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar contornos para encontrar la regla (supongo que la regla es el contorno más largo)
        if not contours:
            return jsonify({'error': 'No se encontraron contornos'}), 400
        else:
            max_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(max_contour)
        # Dibujar contornos en la imagen
        image_with_contours = draw_contours(image, [max_contour])
        # Codificar la imagen con contornos a base64
        _, buffer = cv2.imencode('.png', image_with_contours)
        encoded_image = base64.b64encode(buffer).decode('utf-8')
        # Calibrar la cámara
        known_width_meters = 0.3  # Ancho conocido en metros
        pixel_to_meter_ratio = calibrate_camera(image, known_width_meters, w)
        # Devolver el ancho en píxeles y la relación de calibración
        return jsonify({'referenceWidthPixels': w, 'pixelToMeterRatio': pixel_to_meter_ratio, 'imageWithContours': encoded_image})
    except Exception as e:
        print(f"Error procesando la referencia: {e}")
        return jsonify({'error': 'Error procesando la referencia'}), 500
    
@app.route('/process_measurement', methods=['POST'])
def process_measurement():
    try:
        data = request.json
        image_data = data['imageData']
        # Decodificar la imagen recibida
        encoded_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Convertir a escala de grises y detectar bordes
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 10, 50)
        # Detectar contornos
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Filtrar contornos para encontrar el objeto a medir (usaremos el contorno más grande)
        if not contours:
            return jsonify({'error': 'No se encontraron contornos'}), 400
        else:
            max_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(max_contour)
        # Devolver el ancho en píxeles
        return jsonify({'objectWidthPixels': w})
    except Exception as e:
        print(f"Error procesando la medida: {e}")
        return jsonify({'error': 'Error procesando la medida'}), 500
