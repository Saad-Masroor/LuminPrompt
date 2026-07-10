from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# Create your models here.
class CustomUser(AbstractUser):
    # You can add additional fields here if needed
    """Custom user model that extends Django's AbstractUser."""
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username
    
ACCENT_CHOICES = [
    ('amber', 'Amber (default)'),
    ('cyan', 'Cyan'),
    ('violet', 'Violet'),
    ('rose', 'Rose'),
    ('lime', 'Lime'),
    ('sky', 'Sky'),
]
 
 
class UserProfile(models.Model):
    """
    One-to-one companion to CustomUser for things that are about preference,
    not identity/auth. Kept as a separate model rather than bolting fields
    onto CustomUser so auth stays lean and this can evolve independently.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio = models.CharField(max_length=200, blank=True)
    accent_color = models.CharField(max_length=10, choices=ACCENT_CHOICES, default='amber')
    mute_mic_on_join = models.BooleanField(default=False)
    notification_sound = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f'Profile: {self.user.username}'
 
 
# Convenience accessor so templates/views never need a try/except for users
# created before this model existed — get_or_create handles that gap.
def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile
    