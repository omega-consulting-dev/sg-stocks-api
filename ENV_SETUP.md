# 🔄 Script de Configuration pour Production

Ce script vous aide à configurer rapidement l'environnement de production.

## Utilisation sur le VPS de Production

### Étape 1 : Copier le fichier de production

```bash
cd /opt/sgstock/sg_stocks_api
cp .env.production .env
```

### Étape 2 : Générer les secrets

```bash
# Générer SECRET_KEY Django
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Générer mot de passe aléatoire pour la BDD
openssl rand -base64 32 | tr -d "=+/" | cut -c1-32

# Générer mot de passe admin
openssl rand -base64 24 | tr -d "=+/" | cut -c1-24
```

### Étape 3 : Éditer le fichier .env

```bash
nano .env
```

Modifiez les valeurs suivantes :
- `SECRET_KEY` : Utilisez la clé générée à l'étape 2
- `POSTGRES_PASSWORD` : Utilisez un mot de passe fort
- `DJANGO_SUPERUSER_PASSWORD` : Utilisez un mot de passe fort
- `EMAIL_HOST_USER` : Votre email réel
- `EMAIL_HOST_PASSWORD` : Votre mot de passe d'application Gmail

### Étape 4 : Vérifier la configuration

```bash
# Vérifier que les domaines sont corrects
grep ALLOWED_HOSTS .env
grep BASE_DOMAIN .env

# Vérifier que les mots de passe sont changés
grep PASSWORD .env

# Vérifier que DEBUG est False
grep DEBUG .env
```

## ⚠️ Checklist de Sécurité

- [ ] SECRET_KEY changé et unique
- [ ] POSTGRES_PASSWORD changé et fort (min 20 caractères)
- [ ] DJANGO_SUPERUSER_PASSWORD changé et fort
- [ ] DEBUG=False en production
- [ ] EMAIL configuré avec vraies valeurs
- [ ] ALLOWED_HOSTS contient sg-stocks.com et tous les sous-domaines
- [ ] BASE_DOMAIN=sg-stocks.com
- [ ] Fichier .env non commité dans Git (vérifié dans .gitignore)

## 📝 Différences Dev vs Production

| Paramètre | Développement | Production |
|-----------|---------------|------------|
| ENV_NAME | dev | production |
| DEBUG | True | False |
| SECRET_KEY | dev-key | Clé aléatoire unique |
| ALLOWED_HOSTS | localhost | sg-stocks.com, api.sg-stocks.com, etc. |
| BASE_DOMAIN | localhost | sg-stocks.com |
| POSTGRES_HOST | localhost | postgres (Docker) |
| POSTGRES_PASSWORD | Simple | Fort et sécurisé |
| REDIS_URL | redis://localhost | redis://redis (Docker) |

## 🔐 Stockage Sécurisé des Secrets

Pour une sécurité maximale en production :

1. **Ne jamais commiter .env dans Git**
2. **Utiliser un gestionnaire de secrets** :
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault
   - GitHub Secrets (pour CI/CD)

3. **Backups chiffrés** :
   ```bash
   # Sauvegarder .env chiffré
   gpg -c .env
   # Crée .env.gpg (chiffré)
   ```

4. **Permissions strictes** :
   ```bash
   chmod 600 .env
   chown root:root .env
   ```

## 🚀 Après Configuration

Une fois le fichier .env configuré :

```bash
# Retourner à la racine du projet
cd /opt/sgstock

# Démarrer les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f api

# Vérifier la santé
curl http://localhost/api/health/
```

## 📞 Support

Si vous avez des questions :
- Documentation : [DEPLOYMENT.md](../DEPLOYMENT.md)
- Guide production : [PRODUCTION_GUIDE.md](../PRODUCTION_GUIDE.md)
