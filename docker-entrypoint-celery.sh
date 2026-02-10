#!/bin/bash
set -e

echo "Attente de Redis..."
while ! nc -z $REDIS_HOST $REDIS_PORT; do
    sleep 1
done

echo "Redis prêt! Démarrage de Celery..."

exec celery -A myproject worker -l info
