"""
Tâches asynchrones Celery pour l'application main
"""
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_contact_response_email(self, contact_data, response_text):
    """
    Tâche asynchrone pour envoyer un email de réponse à un message de contact
    
    Args:
        contact_data: Dict avec first_name, last_name, email, message
        response_text: Texte de la réponse à envoyer
    """
    try:
        # Créer le contenu texte
        text_content = f"""
Bonjour {contact_data['first_name']} {contact_data['last_name']},

Merci pour votre message. Voici notre réponse à votre demande :

Votre message :
"{contact_data['message']}"

Notre réponse :
{response_text}

Si vous avez d'autres questions, n'hésitez pas à nous contacter.

Cordialement,
L'équipe SG Stocks

---
© 2026 SG Stocks - Solution de gestion de stock
Cet email a été envoyé automatiquement, merci de ne pas y répondre directement.
"""

        # Créer le contenu HTML
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border: 1px solid #e0e0e0;
            }}
            .message-box {{
                background: white;
                padding: 20px;
                margin: 20px 0;
                border-left: 4px solid #667eea;
                border-radius: 5px;
            }}
            .footer {{
                background: #333;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 0 0 10px 10px;
                font-size: 12px;
            }}
            .label {{
                font-weight: bold;
                color: #667eea;
                margin-bottom: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>SG Stocks</h1>
                <p>Réponse à votre demande de contact</p>
            </div>
            
            <div class="content">
                <p>Bonjour <strong>{contact_data['first_name']} {contact_data['last_name']}</strong>,</p>
                
                <p>Merci pour votre message. Voici notre réponse à votre demande :</p>
                
                <div class="message-box">
                    <div class="label">Votre message :</div>
                    <p style="color: #666; font-style: italic;">"{contact_data['message']}"</p>
                </div>
                
                <div class="message-box">
                    <div class="label">Notre réponse :</div>
                    <p>{response_text}</p>
                </div>
                
                <p>Si vous avez d'autres questions, n'hésitez pas à nous contacter.</p>
                
                <p>Cordialement,<br>
                <strong>L'équipe SG Stocks</strong></p>
            </div>
            
            <div class="footer">
                <p>© 2026 SG Stocks - Solution de gestion de stock</p>
                <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre directement.</p>
            </div>
        </div>
    </body>
    </html>
"""

        # Créer et envoyer l'email
        email = EmailMultiAlternatives(
            subject='Réponse à votre message - SG Stocks',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[contact_data['email']],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"[OK] Email envoyé avec succès à {contact_data['email']}")
        return {
            'success': True,
            'email': contact_data['email'],
            'message': 'Email envoyé avec succès'
        }
        
    except Exception as exc:
        logger.error(f"[ERREUR] Erreur lors de l'envoi de l'email: {exc}")
        # Retry avec backoff exponentiel
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_new_contact_notification(contact_data):
    """
    Tâche asynchrone pour notifier les admins d'un nouveau message de contact
    
    Args:
        contact_data: Dict avec les infos du message de contact
    """
    try:
        admin_emails = settings.ADMIN_NOTIFICATION_EMAILS
        
        if not admin_emails:
            logger.warning("Aucun email admin configuré pour les notifications")
            return
        
        subject = f"Nouveau message de contact - {contact_data['first_name']} {contact_data['last_name']}"
        
        text_content = f"""
Un nouveau message de contact a été reçu :

De : {contact_data['first_name']} {contact_data['last_name']}
Email : {contact_data['email']}
Téléphone : {contact_data.get('phone', 'Non renseigné')}

Message :
{contact_data['message']}

---
Connectez-vous à l'interface admin pour répondre au message.
"""
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        email.send()
        
        logger.info(f"[OK] Notification envoyée aux admins pour le message de {contact_data['email']}")
        return {'success': True}
        
    except Exception as exc:
        logger.error(f"[ERREUR] Erreur lors de l'envoi de la notification admin: {exc}")
        return {'success': False, 'error': str(exc)}
