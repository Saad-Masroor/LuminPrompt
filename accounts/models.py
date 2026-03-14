from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    # You can add additional fields here if needed
    """Custom user model that extends Django's AbstractUser."""
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username
    