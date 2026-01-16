from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _

# Import CompanySettings and ContactMessage
from .models_settings import CompanySettings
from .models_contact import ContactMessage

class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, validators=[UnicodeUsernameValidator()],)

    groups = models.ManyToManyField(
        Group,
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="public_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="public_user_set",
        related_query_name="user",
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']