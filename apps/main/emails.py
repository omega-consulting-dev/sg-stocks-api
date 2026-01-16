"""
Utilitaires pour l'envoi d'emails liés aux messages de contact
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_contact_response_email(contact_message, response_text):
    """
    Envoie un email de réponse au client qui a envoyé un message de contact
    
    Args:
        contact_message: Instance de ContactMessage
        response_text: Texte de la réponse de l'admin
    """
    subject = f"Réponse à votre message - SG Stocks"
    
    # Contexte pour le template
    context = {
        'first_name': contact_message.first_name,
        'last_name': contact_message.last_name,
        'original_message': contact_message.message,
        'response': response_text,
    }
    
    # Message HTML
    html_message = f"""
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
                <p>Bonjour <strong>{context['first_name']} {context['last_name']}</strong>,</p>
                
                <p>Merci pour votre message. Voici notre réponse à votre demande :</p>
                
                <div class="message-box">
                    <div class="label">Votre message :</div>
                    <p style="color: #666; font-style: italic;">"{context['original_message']}"</p>
                </div>
                
                <div class="message-box">
                    <div class="label">Notre réponse :</div>
                    <p>{context['response']}</p>
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
    
    # Message texte simple (fallback)
    text_message = f"""
Bonjour {context['first_name']} {context['last_name']},

Merci pour votre message. Voici notre réponse à votre demande :

Votre message :
"{context['original_message']}"

Notre réponse :
{context['response']}

Si vous avez d'autres questions, n'hésitez pas à nous contacter.

Cordialement,
L'équipe SG Stocks

---
© 2026 SG Stocks - Solution de gestion de stock
Cet email a été envoyé automatiquement, merci de ne pas y répondre directement.
    """
    
    try:
        # Envoyer l'email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact_message.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'envoi de l'email: {e}")
        return False


def send_new_contact_notification(contact_message):
    """
    Envoie une notification aux admins quand un nouveau message de contact est reçu
    
    Args:
        contact_message: Instance de ContactMessage
    """
    subject = f"Nouveau message de contact - {contact_message.first_name} {contact_message.last_name}"
    
    message = f"""
Un nouveau message de contact a été reçu :

De : {contact_message.first_name} {contact_message.last_name}
Email : {contact_message.email}
Téléphone : {contact_message.phone or 'Non fourni'}

Message :
{contact_message.message}

---
Connectez-vous à l'interface d'administration pour répondre.
    """
    
    # Liste des emails admins (à configurer dans settings.py)
    admin_emails = getattr(settings, 'ADMIN_NOTIFICATION_EMAILS', [])
    
    if admin_emails:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"[ERREUR] Erreur lors de l'envoi de la notification admin: {e}")
            return False
    
    return False
