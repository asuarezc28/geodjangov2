#!/bin/bash

# Esperar a que PostgreSQL esté disponible
echo "Waiting for PostgreSQL..."
until pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME"; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done
echo "PostgreSQL is ready!"

# Aplicar migraciones
echo "Applying migrations..."
python manage.py migrate --noinput

# Recolectar archivos estáticos
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Iniciar Gunicorn
echo "Starting Gunicorn..."
exec gunicorn palma_tourism.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --threads 2 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - 