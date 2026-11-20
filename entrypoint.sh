#!/bin/sh
set -e

# Migrasi tabel database
python manage.py migrate --noinput

# Load data awal pengguna, kelas, kartu, dan perangkat jika belum dimuat
python manage.py loaddata initial_data.json || true

# Jalankan Gunicorn di port 7860
exec gunicorn absensi_project.wsgi:application --bind 0.0.0.0:7860 --workers 2 --timeout 120
