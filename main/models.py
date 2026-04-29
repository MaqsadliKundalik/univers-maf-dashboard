from django.db import models
from bot.models import Chat
import uuid
from django.utils import timezone

class GroupStatsLink(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Link for {self.chat.title} (Expires: {self.expires_at})"
