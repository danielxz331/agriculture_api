# from fastapi import FastAPI


# app = FastAPI(debug=True)

import os
import numpy as np
import matplotlib.pyplot as plt
from netCDF4 import Dataset
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from tempfile import NamedTemporaryFile

app = FastAPI()

# Directorio que contiene los archivos HDF
carpeta = 'files'

# Definir un área de búsqueda alrededor de la ciudad (ajusta el radio según lo que necesites)
radio_lat = 0.5  # Tolerancia en latitud
radio_lon = 0.5  # Tolerancia en longitud

# Modelo de Pydantic para recibir las coordenadas en el cuerpo de la solicitud
class Coordenadas(BaseModel):
    lat: float
    lon: float

# Función para procesar cada archivo y extraer datos en función de la latitud y longitud
def procesar_archivo(archivo_hdf, lat_target, lon_target):
    datos = Dataset(archivo_hdf, 'r')
    
    # Extraer las coordenadas geográficas (asegurarse de que sean 2D)
    latitudes = datos.variables['GridCenterLatitude'][:]
    longitudes = datos.variables['GridCenterLongitude'][:]
    
    # Si las latitudes/longitudes son 1D, expandirlas para una cuadrícula 2D
    if latitudes.ndim == 1 and longitudes.ndim == 1:
        lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    else:
        lat_grid = latitudes
        lon_grid = longitudes
    
    # Extraer precipitación, fracción de nubes, presión, y calidad
    precipitacion = np.copy(datos.variables['IR_Precip_Est'][:])  # Usar np.copy() para evitar que sea solo lectura
    fraccion_nubes = np.copy(datos.variables['CldFrcStd'][:])  # Usar np.copy()
    presion_nubes = np.copy(datos.variables['PCldTopStd'][:])  # Usar np.copy()
    calidad = datos.variables['IR_Precip_Est_QC'][:]
    
    # Eliminar valores de relleno no válidos para la presión en la parte superior de las nubes
    presion_nubes = np.where((presion_nubes < 100) | (presion_nubes > 1000), np.nan, presion_nubes)
    
    # Filtrar los datos por calidad (mantener solo calidad 0)
    precip_filtrada = np.where(calidad == 0, precipitacion, np.nan)
    
    # Filtrar los datos geográficamente según las coordenadas deseadas
    filtro_region = (
        (lat_grid >= (lat_target - radio_lat)) & (lat_grid <= (lat_target + radio_lat)) &
        (lon_grid >= (lon_target - radio_lon)) & (lon_grid <= (lon_target + radio_lon))
    )
    
    # Aplicar el filtro geográfico
    precip_region = precip_filtrada[filtro_region]
    nubes_region = fraccion_nubes[filtro_region]
    presion_region = presion_nubes[filtro_region]
    
    # Comprobar si la región tiene datos, si no, devolver NaN
    if precip_region.size == 0:
        promedio_precipitacion = np.nan
    else:
        promedio_precipitacion = np.nanmean(precip_region)
    
    if nubes_region.size == 0:
        promedio_nubes = np.nan
    else:
        promedio_nubes = np.nanmean(nubes_region) / 100.0  # Ajuste de escala
    
    if presion_region.size == 0:
        promedio_presion = np.nan
    else:
        promedio_presion = np.nanmean(presion_region)
    
    datos.close()
    
    return promedio_precipitacion, promedio_nubes, promedio_presion

# Endpoint de FastAPI para procesar la solicitud y devolver la imagen
@app.post("/generate_plot/")
async def generate_plot(coordenadas: Coordenadas):
    archivos = [archivo for archivo in os.listdir(carpeta) if archivo.endswith('.hdf')]

    # Limpiar las listas en cada solicitud
    fechas = []
    precipitaciones_promedio = []
    fraccion_nubes_promedio = []
    presion_nubes_promedio = []

    # Procesar cada archivo y calcular los promedios por día
    for archivo in archivos:
        archivo_path = os.path.join(carpeta, archivo)
        promedio_precipitacion, promedio_nubes, promedio_presion = procesar_archivo(archivo_path, coordenadas.lat, coordenadas.lon)
        
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
    fechas_ordenadas, precip_ordenada, nubes_ordenada, presion_ordenada = zip(*sorted(zip(fechas, precipitaciones_promedio, fraccion_nubes_promedio, presion_nubes_promedio)))

    # Graficar la precipitación promedio por día
    plt.figure(figsize=(12, 8))

    plt.subplot(3, 1, 1)
    plt.plot(fechas_ordenadas, precip_ordenada, marker='o', linestyle='-', color='b')
    plt.xlabel('Fecha')
    plt.ylabel('Precipitación Promedio (mm)')
    plt.title('Precipitación Promedio por Día')
    plt.grid(True)

    plt.subplot(3, 1, 2)
    plt.plot(fechas_ordenadas, nubes_ordenada, marker='o', linestyle='-', color='g')
    plt.xlabel('Fecha')
    plt.ylabel('Fracción de Nubes Promedio (%)')
    plt.title('Fracción de Nubes Promedio por Día')
    plt.grid(True)

    plt.subplot(3, 1, 3)
    plt.plot(fechas_ordenadas, presion_ordenada, marker='o', linestyle='-', color='r')
    plt.xlabel('Fecha')
    plt.ylabel('Presión en la Parte Superior de las Nubes (hPa)')
    plt.title('Presión en la Parte Superior de las Nubes por Día')
    plt.grid(True)

    # Ajustar el diseño
    plt.tight_layout()

    # Guardar la imagen en un archivo temporal
    temp_file = NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name)
    temp_file.close()

    # Devolver la imagen generada
    return FileResponse(temp_file.name, media_type="image/png")
