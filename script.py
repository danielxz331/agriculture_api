from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS  # Importar CORS
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime

matplotlib.use('Agg')

# Crear la aplicación Flask
app = Flask(__name__)

# Habilitar CORS para todo el público
CORS(app, resources={r"/": {"origins": ""}})  # Esto habilita CORS para todos los dominios

# Carpeta donde se almacenan los archivos estáticos (imágenes)
STATIC_DIR = 'static'

# Si no existe la carpeta estática, la creamos
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Función para generar el gráfico basado en latitud y longitud
def generar_grafico(lat, lon):
    # Datos de ejemplo: Generar datos aleatorios basados en lat y lon
    fechas = [datetime(2024, 1, i+1) for i in range(10)]
    precipitaciones_promedio = np.random.rand(10) * 10  # Precipitación aleatoria para 10 días
    fraccion_nubes_promedio = np.random.rand(10) * 100  # Fracción de nubes aleatoria
    presion_nubes_promedio = np.random.rand(10) * 200 + 800  # Presión aleatoria

    plt.figure(figsize=(12, 8))

    # Gráfica de la precipitación
    plt.subplot(3, 1, 1)
    plt.plot(fechas, precipitaciones_promedio, marker='o', linestyle='-', color='b')
    plt.xlabel('Fecha')
    plt.ylabel('Precipitación Promedio (mm)')
    plt.title(f'Precipitación Promedio por Día')
    plt.grid(True)

    # Gráfica de la fracción de nubes
    plt.subplot(3, 1, 2)
    plt.plot(fechas, fraccion_nubes_promedio, marker='o', linestyle='-', color='g')
    plt.xlabel('Fecha')
    plt.ylabel('Fracción de Nubes Promedio (%)')
    plt.title('Fracción de Nubes Promedio por Día')
    plt.grid(True)

    # Gráfica de la presión en la parte superior de las nubes
    plt.subplot(3, 1, 3)
    plt.plot(fechas, presion_nubes_promedio, marker='o', linestyle='-', color='r')
    plt.xlabel('Fecha')
    plt.ylabel('Presión en la Parte Superior de las Nubes (hPa)')
    plt.title('Presión en la Parte Superior de las Nubes por Día')
    plt.grid(True)

    plt.tight_layout()

    # Guardar la imagen en la carpeta estática
    ruta_imagen = os.path.join(STATIC_DIR, 'grafico.png')
    plt.savefig(ruta_imagen)
    plt.close()

    return ruta_imagen

# Ruta principal que genera el gráfico con los parámetros latitud y longitud
@app.route('/generar_grafico', methods=['GET'])
def generar_grafico_endpoint():
    # Obtener los parámetros lat y lon de la solicitud
    lat = request.args.get('lat', default=5.7141, type=float)  # Valor por defecto: Sogamoso
    lon = request.args.get('lon', default=-72.9339, type=float)  # Valor por defecto: Sogamoso

    # Generar el gráfico
    ruta_imagen = generar_grafico(lat, lon)

    # Devolver el gráfico al cliente
    return send_from_directory(STATIC_DIR, 'grafico.png')

# Ruta para comprobar si el servidor está funcionando
@app.route('/status', methods=['GET'])
def status():
    return jsonify({'status': 'ok'})

# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8090)