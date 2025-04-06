#!/bin/bash
set -e

echo "Checking environment..."
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set"
    exit 1
fi

echo "Checking GDAL installation..."
python -c "from osgeo import gdal; print('GDAL Version:', gdal.__version__)"
python -c "from django.contrib.gis.geos import GEOSGeometry"

echo "Waiting for database..."
python << END
import sys
import time
import os
import django
from django.db import connections
from django.db.utils import OperationalError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palma_tourism.settings')
django.setup()

print("Database configuration:")
db_url = os.getenv('DATABASE_URL')
print(f"DATABASE_URL is {'set' if db_url else 'not set'}")

retries = 30
while retries > 0:
    try:
        print(f"Attempting database connection... ({retries} attempts left)")
        connections['default'].ensure_connection()
        print("Database connection successful!")
        break
    except OperationalError as e:
        retries -= 1
        if retries == 0:
            print(f"Could not connect to database: {str(e)}")
            sys.exit(1)
        print(f"Database connection failed: {str(e)}")
        print("Retrying in 1 second...")
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
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --capture-output 