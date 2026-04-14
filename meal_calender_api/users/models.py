from django.db import models
from django.contrib.auth.models import AbstractUser

# users/models.py
class User(AbstractUser):
    avatar         = models.ImageField(upload_to="avatars/", blank=True)
    date_of_birth  = models.DateField(null=True)
    created_at     = models.DateTimeField(auto_now_add=True)

