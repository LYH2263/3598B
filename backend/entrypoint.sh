#!/bin/bash
set -e

python scripts/wait_for_db.py
python manage.py migrate --noinput
python manage.py seed_data
python manage.py collectstatic --noinput

exec gunicorn campus_pay.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
