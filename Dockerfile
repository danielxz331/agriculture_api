# Utilizar una imagen base de Python 3.10
FROM python:3.10-slim

# Instalar las dependencias del sistema necesarias para HDF5 y HDF4
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf4-alt-dev \
    build-essential \
    zlib1g-dev \
    && apt-get clean

# Copiar el archivo de requerimientos
COPY ./requirements.txt /app/requirements.txt

# Instalar las dependencias de Python
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copiar el código de la aplicación al directorio de trabajo
COPY . /app

# Establecer el directorio de trabajo en /app
WORKDIR /app

# Exponer el puerto en el que se ejecutará la aplicación
EXPOSE 8888

# Comando para iniciar la aplicación
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8888"]
