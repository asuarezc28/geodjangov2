FROM python:3.10

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    binutils \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    libproj-dev \
    libgeos-dev \
    postgresql-client \
    # Dependencias para Pillow
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno para GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so

# Crear y activar el directorio de trabajo
WORKDIR /app

# Instalar GDAL Python antes que nada
RUN pip install --no-binary :all: GDAL==`gdal-config --version`

# Copiar e instalar requisitos
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# Hacer ejecutable el script de inicio
COPY start.sh .
RUN chmod +x start.sh

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["./start.sh"] 