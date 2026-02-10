#!/bin/bash
set -e

echo "Attente de la base de données..."
while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
    sleep 1
done

echo "Base de données prête!"

# Exécuter les migrations
echo "Exécution des migrations..."
python manage.py migrate --noinput

# Collecter les fichiers statiques
echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

# Créer un superutilisateur si nécessaire
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created.')
else:
    print('Superuser already exists.')
END
fi

# Exécuter la commande passée en argument
exec "$@"
