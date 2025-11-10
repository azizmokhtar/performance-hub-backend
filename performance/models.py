# performance/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class TrainingType(models.TextChoices):
    RECOVERY = "RECOVERY", "Recovery"
    STRENGTH = "STRENGTH", "Strength"
    CONDITIONING = "CONDITIONING", "Conditioning"
    TECHNICAL = "TECHNICAL", "Technical"
    TACTICAL = "TACTICAL", "Tactical"
    MATCH = "MATCH", "Match"

class TrainingSession(models.Model):
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='sessions')
    season = models.ForeignKey('teams.Season', on_delete=models.SET_NULL, null=True, blank=True)
    session_type = models.CharField(max_length=16, choices=TrainingType.choices, default=TrainingType.TECHNICAL)
    title = models.CharField(max_length=120)
    start = models.DateTimeField()
    end = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=['team','start'])]

class Attendance(models.Model):
    PRESENT = "PRESENT"; ABSENT = "ABSENT"; EXCUSED = "EXCUSED"; LATE = "LATE"
    STATUS_CHOICES = ((PRESENT,"Present"), (ABSENT,"Absent"), (EXCUSED,"Excused"), (LATE,"Late"))

    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name='attendance')
    membership = models.ForeignKey('teams.TeamMembership', on_delete=models.CASCADE, related_name='attendance')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PRESENT)
    minutes_participated = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('session','membership')]

class WellnessLog(models.Model):
    """
    Simple daily wellness (self-report). 1–5 Likert.
    """
    membership = models.ForeignKey('teams.TeamMembership', on_delete=models.CASCADE, related_name='wellness_logs')
    date = models.DateField(default=timezone.now)
    sleep_quality = models.PositiveSmallIntegerField(null=True, blank=True)  # 1..5
    mood = models.PositiveSmallIntegerField(null=True, blank=True)           # 1..5
    soreness = models.PositiveSmallIntegerField(null=True, blank=True)       # 1..5
    stress = models.PositiveSmallIntegerField(null=True, blank=True)         # optional 1..5
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('membership','date')]
        indexes = [models.Index(fields=['membership','date'])]

class SessionRPE(models.Model):
    """
    Internal load (sRPE = RPE x duration in minutes).
    """
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name='srpe')
    membership = models.ForeignKey('teams.TeamMembership', on_delete=models.CASCADE, related_name='srpe')
    rpe_0_10 = models.DecimalField(max_digits=4, decimal_places=1)  # e.g. 7.5
    duration_min = models.PositiveIntegerField()                     # typically session length or minutes_participated
    load_au = models.PositiveIntegerField()                          # computed: round(rpe * duration)

    class Meta:
        unique_together = [('session','membership')]
        indexes = [models.Index(fields=['membership','session'])]

class DailyLoad(models.Model):
    """
    Roll-up per athlete per date to support ACWR/EWMA fast.
    """
    membership = models.ForeignKey('teams.TeamMembership', on_delete=models.CASCADE, related_name='daily_loads')
    date = models.DateField()
    internal_load_au = models.PositiveIntegerField(default=0)  # sum of SessionRPE per day
    external_load_pl = models.PositiveIntegerField(default=0)  # optional: sum of GPS PlayerLoad, etc.

    class Meta:
        unique_together = [('membership','date')]
        indexes = [models.Index(fields=['membership','date'])]

class LoadACWR(models.Model):
    """
    Store EWMA-based acute/chronic + ratio snapshots per day.
    """
    membership = models.ForeignKey('teams.TeamMembership', on_delete=models.CASCADE, related_name='acwr')
    date = models.DateField()
    acute_ewma = models.FloatField()
    chronic_ewma = models.FloatField()
    ratio = models.FloatField()
    source = models.CharField(max_length=16, default="INTERNAL")  # INTERNAL / EXTERNAL

    class Meta:
        unique_together = [('membership','date','source')]
        indexes = [models.Index(fields=['membership','date'])]
