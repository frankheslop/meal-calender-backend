from django.contrib.auth.models import AbstractUser
from django.db import models


# users/models.py
class CustomUser(AbstractUser):
    """Custom user model that extends Django's AbstractUser."""

    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    timezone = models.CharField(max_length=64, default="UTC")


# Backward-compatible alias for modules importing `User` from this file.
User = CustomUser
