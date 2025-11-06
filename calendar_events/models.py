from django.db import models
from django.conf import settings # To refer to AUTH_USER_MODEL
from teams.models import Team # Assuming teams app is already defined

class Event(models.Model):
    EVENT_TYPE_CHOICES = (
        ('TRAINING', 'Training Session'),
        ('MATCH', 'Match'),
        ('MEETING', 'Meeting'),
        ('TRAVEL', 'Travel'),
        ('RECOVERY', 'Recovery Session'),
        ('OTHER', 'Other'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='TRAINING')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Don't delete event if creator leaves
        null=True, blank=True,
        related_name='created_events',
        limit_choices_to={'role__in': ['COACH', 'ADMIN']}
    )
    is_mandatory = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.event_type}: {self.title} ({self.team.name})"


class Attendance(models.Model):
    ATTENDANCE_STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('INJURED', 'Injured'),
        ('EXCUSED', 'Excused'),
        ('PENDING_CONFIRMATION', 'Pending Confirmation'),
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_attendances',
        limit_choices_to={'role': 'PLAYER'}
    )
    status = models.CharField(max_length=25, choices=ATTENDANCE_STATUS_CHOICES, default='PENDING_CONFIRMATION')
    notes = models.TextField(null=True, blank=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reported_attendances'
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'player') # Each player can only have one attendance record per event
        ordering = ['player__last_name', 'player__first_name']
        verbose_name_plural = "Attendances"

    def __str__(self):
        return f"{self.player.get_full_name()} - {self.event.title}: {self.status}"