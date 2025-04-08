#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    binutils \
    libproj-dev \
    libgeos-dev

# Install Python dependencies
pip install --upgrade pip
pip install GDAL==$(gdal-config --version)
pip install -r requirements.txt

# Run Django commands
python manage.py collectstatic --no-input
python manage.py migrate 