"""
Service pour automatiser la création d'enregistrements DNS Cloudflare
lors de la création de tenants.
"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class CloudflareService:
    """
    Service pour gérer les enregistrements DNS via l'API Cloudflare.
    """
    
    BASE_URL = "https://api.cloudflare.com/client/v4"
    
    def __init__(self):
        self.api_token = getattr(settings, 'CLOUDFLARE_API_TOKEN', None)
        self.zone_id = getattr(settings, 'CLOUDFLARE_ZONE_ID', None)
        self.server_ip = getattr(settings, 'SERVER_IP', '76.13.49.22')
        
    def _get_headers(self):
        """Retourne les headers pour l'API Cloudflare."""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }
    
    def create_dns_record(self, subdomain, ip_address=None, proxied=True):
        """
        Crée un enregistrement DNS A pour un sous-domaine.
        
        Args:
            subdomain (str): Le sous-domaine à créer (ex: "omega")
            ip_address (str): L'adresse IP cible (défaut: SERVER_IP)
            proxied (bool): Activer le proxy Cloudflare (défaut: True)
            
        Returns:
            dict: Réponse de l'API Cloudflare ou None en cas d'erreur
        """
        if not self.api_token or not self.zone_id:
            logger.warning("Cloudflare API token ou Zone ID non configuré - enregistrement DNS ignoré")
            return None
            
        ip_address = ip_address or self.server_ip
        
        # Vérifier si l'enregistrement existe déjà
        existing = self.get_dns_record(subdomain)
        if existing:
            logger.info(f"Enregistrement DNS {subdomain}.sg-stocks.com existe déjà (ID: {existing['id']})")
            return existing
        
        # Créer le nouvel enregistrement
        url = f"{self.BASE_URL}/zones/{self.zone_id}/dns_records"
        
        data = {
            'type': 'A',
            'name': subdomain,
            'content': ip_address,
            'ttl': 1,  # Auto (géré par Cloudflare)
            'proxied': proxied,
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success'):
                logger.info(f"✅ Enregistrement DNS créé: {subdomain}.sg-stocks.com → {ip_address} (proxied={proxied})")
                return result.get('result')
            else:
                logger.error(f"❌ Échec création DNS {subdomain}: {result.get('errors')}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"❌ Erreur API Cloudflare lors de la création DNS {subdomain}: {e}")
            return None
    
    def get_dns_record(self, subdomain):
        """
        Vérifie si un enregistrement DNS existe pour un sous-domaine.
        
        Args:
            subdomain (str): Le sous-domaine à vérifier
            
        Returns:
            dict: L'enregistrement DNS ou None s'il n'existe pas
        """
        if not self.api_token or not self.zone_id:
            return None
            
        url = f"{self.BASE_URL}/zones/{self.zone_id}/dns_records"
        params = {
            'type': 'A',
            'name': f'{subdomain}.sg-stocks.com',
        }
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success') and result.get('result'):
                return result['result'][0]
            return None
            
        except requests.RequestException as e:
            logger.error(f"Erreur lors de la vérification DNS {subdomain}: {e}")
            return None
    
    def delete_dns_record(self, subdomain):
        """
        Supprime un enregistrement DNS.
        
        Args:
            subdomain (str): Le sous-domaine à supprimer
            
        Returns:
            bool: True si supprimé avec succès, False sinon
        """
        if not self.api_token or not self.zone_id:
            logger.warning("Cloudflare API non configuré - suppression DNS ignorée")
            return False
            
        # Récupérer l'ID de l'enregistrement
        record = self.get_dns_record(subdomain)
        if not record:
            logger.warning(f"Enregistrement DNS {subdomain}.sg-stocks.com introuvable")
            return False
        
        url = f"{self.BASE_URL}/zones/{self.zone_id}/dns_records/{record['id']}"
        
        try:
            response = requests.delete(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success'):
                logger.info(f"✅ Enregistrement DNS supprimé: {subdomain}.sg-stocks.com")
                return True
            else:
                logger.error(f"❌ Échec suppression DNS {subdomain}: {result.get('errors')}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"❌ Erreur API Cloudflare lors de la suppression DNS {subdomain}: {e}")
            return False
