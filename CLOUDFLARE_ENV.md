# Configuration Cloudflare pour la création automatique des enregistrements DNS
# Requis pour l'automatisation de la création des sous-domaines tenants

# API Token Cloudflare (Permissions: Zone.DNS Edit pour sg-stocks.com)
# Créer sur : https://dash.cloudflare.com/profile/api-tokens
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here

# Zone ID du domaine sg-stocks.com
# Trouver dans: Cloudflare Dashboard → sg-stocks.com → Overview (colonne de droite)
CLOUDFLARE_ZONE_ID=your_zone_id_here

# IP du serveur (par défaut: 76.13.49.22)
SERVER_IP=76.13.49.22
