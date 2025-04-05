FROM python:3.8

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    binutils \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    libproj-dev \
    libgeos-dev \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno para GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Crear y establecer el directorio de trabajo
WORKDIR /app

# Copiar requirements.txt primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear script de inicio
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Current directory: $(pwd)"\n\
echo "Listing directory contents:"\n\
ls -la\n\
\n\
echo "Python version:"\n\
python --version\n\
\n\
echo "Checking GDAL installation:"\n\
python -c "from osgeo import gdal; print(gdal.__version__)"\n\
\n\
echo "Running migrations..."\n\
python manage.py migrate --noinput\n\
\n\
echo "Collecting static files..."\n\
python manage.py collectstatic --noinput\n\
\n\
echo "Starting Gunicorn with debug logging..."\n\
exec gunicorn palma_tourism.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 2 \
    --log-level debug \
    --timeout 120 \
    --error-logfile - \
    --access-logfile - \
    --capture-output' > start.sh

RUN chmod +x start.sh

# Exponer el puerto (Railway lo sobreescribirá con $PORT)
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["./start.sh"] 