from django.db import models
from django.utils import timezone


class ContactMessage(models.Model):
    """Modèle pour stocker les messages de contact des clients"""
    
    STATUS_CHOICES = [
        ('new', 'Nouveau'),
        ('read', 'Lu'),
        ('replied', 'Répondu'),
        ('archived', 'Archivé'),
    ]
    
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    message = models.TextField(verbose_name="Message")
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Statut"
    )
    
    response = models.TextField(
        blank=True,
        null=True,
        verbose_name="Réponse"
    )
    
    responded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de réponse"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    
    class Meta:
        db_table = 'contact_messages'
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"
    
    def mark_as_read(self):
        """Marquer le message comme lu"""
        if self.status == 'new':
            self.status = 'read'
            self.save()
    
    def mark_as_replied(self, response_text):
        """Marquer le message comme répondu"""
        self.status = 'replied'
        self.response = response_text
        self.responded_at = timezone.now()
        self.save()
