from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from netCDF4 import Dataset
from datetime import datetime

matplotlib.use('Agg')  # Cambiar el backend de matplotlib para evitar problemas con hilos

# Crear la aplicación Flask
app = Flask(__name__)

# Habilitar CORS para todo el público
CORS(app, resources={r"/*": {"origins": "*"}})

# Carpeta donde se almacenan los archivos estáticos (imágenes)
STATIC_DIR = 'static'
CARPETA_HDF = 'files'  # Carpeta donde están los archivos HDF

# Si no existe la carpeta estática, la creamos
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Función para procesar los archivos HDF y extraer datos basados en la latitud y longitud
def procesar_archivo(archivo_hdf, lat_target, lon_target, radio_lat=0.5, radio_lon=0.5):
    datos = Dataset(archivo_hdf, 'r')
    
    # Extraer las coordenadas geográficas
    latitudes = datos.variables['GridCenterLatitude'][:]
    longitudes = datos.variables['GridCenterLongitude'][:]
    
    # Si las latitudes/longitudes son 1D, expandirlas para una cuadrícula 2D
    if latitudes.ndim == 1 and longitudes.ndim == 1:
        lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    else:
        lat_grid = latitudes
        lon_grid = longitudes
    
    # Extraer precipitación, fracción de nubes, presión y calidad
    precipitacion = np.copy(datos.variables['IR_Precip_Est'][:])
    fraccion_nubes = np.copy(datos.variables['CldFrcStd'][:])
    presion_nubes = np.copy(datos.variables['PCldTopStd'][:])
    calidad = datos.variables['IR_Precip_Est_QC'][:]
    
    # Eliminar valores de relleno no válidos para la presión
    presion_nubes = np.where((presion_nubes < 100) | (presion_nubes > 1000), np.nan, presion_nubes)
    
    # Filtrar los datos por calidad (mantener solo calidad 0)
    precip_filtrada = np.where(calidad == 0, precipitacion, np.nan)
    
    # Filtrar los datos geográficamente según las coordenadas deseadas
    filtro_region = (
        (lat_grid >= (lat_target - radio_lat)) & (lat_grid <= (lat_target + radio_lat)) &
        (lon_grid >= (lon_target - radio_lon)) & (lon_grid <= (lon_target + radio_lon))
    )
    
    precip_region = precip_filtrada[filtro_region]
    nubes_region = fraccion_nubes[filtro_region]
    presion_region = presion_nubes[filtro_region]
    
    # Calcular los promedios
    promedio_precipitacion = np.nanmean(precip_region) if precip_region.size > 0 else np.nan
    promedio_nubes = np.nanmean(nubes_region) / 100.0 if nubes_region.size > 0 else np.nan
    promedio_presion = np.nanmean(presion_region) if presion_region.size > 0 else np.nan

    datos.close()
    
    return promedio_precipitacion, promedio_nubes, promedio_presion

# Función para generar el gráfico basado en latitud y longitud
def generar_grafico(lat, lon):
    # Obtener lista de archivos HDF en la carpeta
    archivos = [archivo for archivo in os.listdir(CARPETA_HDF) if archivo.endswith('.hdf')]

    fechas = []
    precipitaciones_promedio = []
    fraccion_nubes_promedio = []
    presion_nubes_promedio = []

    # Procesar cada archivo y calcular los promedios por día
    for archivo in archivos:
        archivo_path = os.path.join(CARPETA_HDF, archivo)
        promedio_precipitacion, promedio_nubes, promedio_presion = procesar_archivo(archivo_path, lat, lon)
        
        # Extraer la fecha del nombre del archivo (formato esperado YYYY.MM.DD)
        try:
            fecha_str = archivo.split('.')[1] + '.' + archivo.split('.')[2] + '.' + archivo.split('.')[3]
            fecha = datetime.strptime(fecha_str, '%Y.%m.%d')
        except ValueError as e:
            print(f"Error procesando la fecha del archivo {archivo}: {e}")
            continue
        
        # Almacenar los resultados
        fechas.append(fecha)
        precipitaciones_promedio.append(promedio_precipitacion)
        fraccion_nubes_promedio.append(promedio_nubes)
        presion_nubes_promedio.append(promedio_presion)

    # Ordenar por fecha
    fechas, precipitaciones_promedio, fraccion_nubes_promedio, presion_nubes_promedio = zip(*sorted(zip(fechas, precipitaciones_promedio, fraccion_nubes_promedio, presion_nubes_promedio)))

    # Graficar los resultados
    plt.figure(figsize=(12, 8))

    # Gráfica de la precipitación
    plt.subplot(3, 1, 1)
    plt.plot(fechas, precipitaciones_promedio, marker='o', linestyle='-', color='b')
    plt.xlabel('Fecha')
    plt.ylabel('Precipitación Promedio (mm)')
    plt.title('Precipitación Promedio por Día')
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