FROM python:3.8-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema y GDAL
RUN apt-get update && apt-get install -y \
    binutils \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    libproj-dev \
    libgeos-dev \
    postgresql-client \
    gcc \
    python3-dev \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

# Configurar GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so
ENV GDAL_DATA=/usr/share/gdal
ENV PROJ_LIB=/usr/share/proj

# Crear directorio de la aplicación
WORKDIR /app

# Instalar GDAL Python primero
RUN pip install --no-cache-dir GDAL==$(gdal-config --version)

# Copiar requirements.txt e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verificar la instalación de GDAL
RUN python -c "from osgeo import gdal; print('GDAL Version:', gdal.__version__)"
RUN python -c "from django.contrib.gis.geos import GEOSGeometry"

# Copiar el proyecto
COPY . .

# Script de inicio
COPY start.sh .
RUN chmod +x start.sh

# Puerto por defecto
EXPOSE 8000

# Comando por defecto
CMD ["./start.sh"] 