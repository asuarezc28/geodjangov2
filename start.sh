#!/bin/bash
set -e

echo "Checking environment..."
if [ -z "$DATABASE_PUBLIC_URL" ]; then
    echo "ERROR: DATABASE_PUBLIC_URL is not set"
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
import psycopg2
from urllib.parse import urlparse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palma_tourism.settings')
django.setup()

print("Database configuration:")
db_url = os.getenv('DATABASE_PUBLIC_URL')
print(f"DATABASE_PUBLIC_URL is {'set' if db_url else 'not set'}")

# Parse the URL to get connection details
url = urlparse(db_url)
dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port

# Try to connect and create PostGIS extension
try:
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    conn.autocommit = True
    cur = conn.cursor()
    print("Creating PostGIS extensions if they don't exist...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
    cur.close()
    conn.close()
    print("PostGIS extensions created successfully!")
except Exception as e:
    print(f"Error creating PostGIS extensions: {str(e)}")
    # Continue anyway as the extensions might already exist

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

echo "Creating superuser if it doesn't exist..."
python << END
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palma_tourism.settings')
django.setup()

User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created successfully!")
else:
    print("Superuser already exists.")
END

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