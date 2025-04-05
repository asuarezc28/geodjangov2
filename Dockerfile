FROM python:3.8

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    binutils \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    libproj-dev \
    libgeos-dev \
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
RUN echo "#!/bin/bash\npython manage.py migrate\npython manage.py collectstatic --noinput\ngunicorn palma_tourism.wsgi:application --bind 0.0.0.0:\$PORT" > start.sh
RUN chmod +x start.sh

# Exponer el puerto (Railway lo sobreescribirá con $PORT)
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["./start.sh"] 