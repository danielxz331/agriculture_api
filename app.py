import os
import h5py
from pyhdf.SD import SD, SDC
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from tempfile import NamedTemporaryFile
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

app = FastAPI()

# Definir un área de búsqueda alrededor de la ciudad (ajusta el radio según lo que necesites)
radio_lat = 0.5  # Tolerancia en latitud
radio_lon = 0.5  # Tolerancia en longitud

# Modelo de Pydantic para recibir las coordenadas en el cuerpo de la solicitud
class Coordenadas(BaseModel):
    lat: float
    lon: float

# Función para procesar archivos HDF4
def procesar_hdf4(datos, lat_target, lon_target):
    # Aquí puedes procesar el archivo HDF4
    datasets_dic = datos.datasets()
    print(f"Datasets disponibles en HDF4: {datasets_dic.keys()}")
    
    latitudes = datos.select('GridCenterLatitude')[:]
    longitudes = datos.select('GridCenterLongitude')[:]
    
    precip_region, nubes_region, presion_region = np.nan, np.nan, np.nan  # Coloca la lógica de procesamiento aquí
    
    return precip_region, nubes_region, presion_region

# Función para procesar archivos HDF5
def procesar_hdf5(datos, lat_target, lon_target):
    # Aquí puedes procesar el archivo HDF5
    latitudes = datos['GridCenterLatitude'][:]
    longitudes = datos['GridCenterLongitude'][:]
    
    precip_region, nubes_region, presion_region = np.nan, np.nan, np.nan  # Coloca la lógica de procesamiento aquí
    
    return precip_region, nubes_region, presion_region

# Función para intentar abrir el archivo como HDF4 o HDF5
def procesar_archivo(archivo_hdf, lat_target, lon_target):
    if not os.path.exists(archivo_hdf):
        print(f"Archivo {archivo_hdf} no encontrado.")
        return None, None, None

    try:
        # Intentar abrir con h5py como HDF5
        with h5py.File(archivo_hdf, 'r') as datos:
            print(f"Archivo {archivo_hdf} es un archivo HDF5.")
            return procesar_hdf5(datos, lat_target, lon_target)
    except OSError as e:
        print(f"Archivo {archivo_hdf} no es un archivo HDF5: {e}")

    try:
        # Intentar abrir el archivo como HDF4
        datos = SD(archivo_hdf, SDC.READ)
        print(f"Archivo {archivo_hdf} es un archivo HDF4.")
        return procesar_hdf4(datos, lat_target, lon_target)
    except Exception as e:
        print(f"Error abriendo {archivo_hdf}: {e}")
        return None, None, None

# Endpoint de FastAPI para procesar la solicitud y devolver la imagen
@app.post("/generate_plot/")
async def generate_plot(coordenadas: Coordenadas):
    carpeta = 'files'  # Directorio que contiene los archivos HDF
    archivos = [archivo for archivo in os.listdir(carpeta) if archivo.endswith('.hdf')]

    fechas = []
    precipitaciones_promedio = []
    fraccion_nubes_promedio = []
    presion_nubes_promedio = []

    for archivo in archivos:
        archivo_path = os.path.join(carpeta, archivo)
        promedio_precipitacion, promedio_nubes, promedio_presion = procesar_archivo(archivo_path, coordenadas.lat, coordenadas.lon)
        
        if promedio_precipitacion is None:
            continue

        # Extraer la fecha del nombre del archivo (formato esperado YYYY.MM.DD)
        try:
            fecha_str = archivo.split('.')[1] + '.' + archivo.split('.')[2] + '.' + archivo.split('.')[3]
            fecha = datetime.strptime(fecha_str, '%Y.%m.%d')
        except ValueError as e:
            print(f"Error procesando la fecha del archivo {archivo}: {e}")
            continue
        
        fechas.append(fecha)
        precipitaciones_promedio.append(promedio_precipitacion)
        fraccion_nubes_promedio.append(promedio_nubes)
        presion_nubes_promedio.append(promedio_presion)

    # Graficar los resultados
    plt.figure(figsize=(12, 8))

    plt.subplot(3, 1, 1)
    plt.plot(fechas, precipitaciones_promedio, marker='o', linestyle='-', color='b')
    plt.xlabel('Fecha')
    plt.ylabel('Precipitación Promedio (mm)')
    plt.title('Precipitación Promedio por Día')
    plt.grid(True)

    plt.subplot(3, 1, 2)
    plt.plot(fechas, fraccion_nubes_promedio, marker='o', linestyle='-', color='g')
    plt.xlabel('Fecha')
    plt.ylabel('Fracción de Nubes Promedio (%)')
    plt.title('Fracción de Nubes Promedio por Día')
    plt.grid(True)

    plt.subplot(3, 1, 3)
    plt.plot(fechas, presion_nubes_promedio, marker='o', linestyle='-', color='r')
    plt.xlabel('Fecha')
    plt.ylabel('Presión en la Parte Superior de las Nubes (hPa)')
    plt.title('Presión en la Parte Superior de las Nubes por Día')
    plt.grid(True)

    # Guardar la imagen en un archivo temporal
    temp_file = NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name)
    temp_file.close()

    # Devolver la imagen generada
    return FileResponse(temp_file.name, media_type="image/png")
