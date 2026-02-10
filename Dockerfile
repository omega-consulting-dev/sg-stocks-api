# Dockerfile pour SG Stocks API (Django Backend)
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les fichiers de requirements
COPY requirements/common.txt requirements/common.txt
COPY requirements/production.txt requirements/production.txt

# Installer les dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements/production.txt && \
    pip install gunicorn psycopg2-binary

# Copier le code de l'application
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chmod -R 755 /app/staticfiles /app/media /app/logs

# Exposer le port
EXPOSE 8000

# Script d'entrée
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "myproject.wsgi:application"]
