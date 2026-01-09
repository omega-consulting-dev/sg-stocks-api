from django.contrib.auth.models import User
from django.db import models

class SuperAdminProfile(models.Model):
    """
    Profil pour les super administrateurs
    Étend le modèle User Django par défaut
    Existe uniquement dans le schéma public
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='superadmin_profile')
    full_name = models.CharField(max_length=255, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'superadmin_profiles'
        verbose_name = 'Profil Super Administrateur'
        verbose_name_plural = 'Profils Super Administrateurs'
    
    def __str__(self):
        return f"SuperAdmin: {self.full_name or self.user.username}"