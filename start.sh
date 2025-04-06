#!/bin/bash

# Dar tiempo a que PostgreSQL esté disponible
echo "Waiting for PostgreSQL..."
sleep 10
echo "Continuing with deployment..."

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