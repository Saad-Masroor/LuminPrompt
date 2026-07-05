# rooms/models.py
import uuid
from django.db import models
from django.conf import settings


class Room(models.Model):
    name        = models.CharField(max_length=100)
    slug        = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    description = models.TextField(blank=True)
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_rooms')
    members     = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='joined_rooms', blank=True)
    # Anyone kicked ends up here. The invite link no longer lets them back in
    # until an owner removes them from this list (unban isn't built yet).
    banned_members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='banned_from_rooms', blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/rooms/{self.slug}/'


class Interaction(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='interactions')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transcript_snapshot = models.JSONField()
    ai_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'AI interaction in {self.room.name} at {self.created_at:%Y-%m-%d %H:%M}'


class ChatMessage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.username}: {self.message[:30]}'


class TranscriptLine(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='transcript_lines')
    speaker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.speaker.username}: {self.text[:30]}'