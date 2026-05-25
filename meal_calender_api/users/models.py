from django.db import models
from django.contrib.auth.models import AbstractUser

# users/models.py
class CustomUser(AbstractUser):
    """Custom user model that extends Django's AbstractUser."""
    # Add any additional fields here if needed in the future
    pass

