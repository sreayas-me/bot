#!/bin/bash

# Set environment variables
export FLASK_APP=dashboard/app.py
export FLASK_ENV=production
export PYTHONPATH=/opt/render/project/src

# Change to app directory
cd /opt/render/project/src

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:$PORT wsgi:app \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --capture-output
