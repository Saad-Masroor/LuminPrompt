# rooms/models.py
import uuid
from django.db import models
from django.conf import settings


class Room(models.Model):
    """
    A collaborative room where users work on AI prompts together.

    - slug: unique URL-friendly identifier (e.g. /rooms/abc123)
    - created_by: the user who created the room
    - members: users who have joined
    - is_active: allows soft-disabling rooms without deleting
    """
    name        = models.CharField(max_length=100)
    slug        = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    description = models.TextField(blank=True)
    created_by  = models.ForeignKey(
                    settings.AUTH_USER_MODEL,
                    on_delete=models.CASCADE,
                    related_name='created_rooms'
                  )
    members     = models.ManyToManyField(
                    settings.AUTH_USER_MODEL,
                    related_name='joined_rooms',
                    blank=True
                  )
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/rooms/{self.slug}/'