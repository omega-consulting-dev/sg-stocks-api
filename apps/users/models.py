from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator

class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, validators=[UnicodeUsernameValidator()],)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']