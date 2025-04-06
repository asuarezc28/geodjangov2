#!/bin/bash
set -e

echo "Checking GDAL installation..."
python -c "from osgeo import gdal; print('GDAL Version:', gdal.__version__)"
python -c "from django.contrib.gis.geos import GEOSGeometry"

echo "Waiting for database..."
python << END
import sys
import time
import psycopg2
from urllib.parse import urlparse
import os

# Get database URL from environment
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("No DATABASE_URL found")
    sys.exit(1)

# Parse the URL
url = urlparse(database_url)
dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port

# Wait for database to be ready
for _ in range(30):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        print("Database is ready!")
        break
    except psycopg2.OperationalError:
        print("Waiting for database...")
        time.sleep(1)
END

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn palma_tourism.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - 