#!/bin/sh
set -eu
python -m flask --app wsgi db upgrade
python -c "from wsgi import app; from app.models import ensure_model_record; app.app_context().push(); ensure_model_record()"
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 2 --timeout 90 --access-logfile - --error-logfile - wsgi:app
