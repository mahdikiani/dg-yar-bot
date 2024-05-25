#!/bin/bash
# echo "Collect static files"
# python manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Start server
echo "Starting server"
/usr/local/bin/gunicorn server.wsgi:application -w 2 -b :80 --reload