from django.db import models
from django.conf import settings # To refer to AUTH_USER_MODEL
from teams.models import Team # Assuming teams app is already defined

class Conversation(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True) # For group chats
    is_group_chat = models.BooleanField(default=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.name:
            return self.name
        # For direct messages, create a name from participants
        if not self.is_group_chat and self.participants.count() == 2:
            return f"DM: {self.participants.first().get_full_name()} - {self.participants.last().get_full_name()}"
        return f"Conversation {self.id}"

class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # is_read is typically tracked per-user, not on the message itself for simplicity in MVP.
    # For a scalable solution, consider a `ReadReceipt` model (Message, User, timestamp).
    # For MVP, we'll assume a message is 'read' once fetched by a participant.

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.email} in {self.conversation}"

class Announcement(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Don't delete announcement if sender leaves
        null=True, blank=True,
        related_name='sent_announcements',
        limit_choices_to={'role__in': ['COACH', 'STAFF', 'ADMIN']}
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_urgent = models.BooleanField(default=False)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_announcements',
        blank=True
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Announcement: {self.title} by {self.sender.email if self.sender else 'N/A'}"