#!/bin/bash
set -e

echo "Checking GDAL installation..."
python -c "from osgeo import gdal; print('GDAL Version:', gdal.__version__)"
python -c "from django.contrib.gis.geos import GEOSGeometry"

echo "Waiting for database..."
python << END
import sys
import time
from django.db import connections
from django.db.utils import OperationalError
import django
import os

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palma_tourism.settings')
django.setup()

# Try to connect to the database
retries = 30
while retries > 0:
    try:
        connections['default'].ensure_connection()
        print("Database connection successful!")
        break
    except OperationalError as e:
        retries -= 1
        if retries == 0:
            print("Could not connect to database!")
            print(f"Error: {e}")
            sys.exit(1)
        print(f"Database connection failed. {retries} retries left...")
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
    --error-logfile - \
    --log-level debug 