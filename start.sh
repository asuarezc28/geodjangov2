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
import os
from urllib.parse import urlparse

database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("No DATABASE_URL found")
    sys.exit(1)

print(f"Attempting to connect to database...")
url = urlparse(database_url)
print(f"Host: {url.hostname}")
print(f"Port: {url.port}")
print(f"Database: {url.path[1:]}")

# Wait for database to be ready
max_retries = 30
retry_count = 0
while retry_count < max_retries:
    try:
        print(f"Connection attempt {retry_count + 1}/{max_retries}")
        conn = psycopg2.connect(
            database_url,
            connect_timeout=5
        )
        conn.close()
        print("Database connection successful!")
        break
    except psycopg2.OperationalError as e:
        print(f"Database connection failed: {e}")
        retry_count += 1
        if retry_count < max_retries:
            print("Retrying in 1 second...")
            time.sleep(1)
        else:
            print("Max retries reached. Exiting.")
            sys.exit(1)
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
    --error-logfile - \
    --log-level debug 