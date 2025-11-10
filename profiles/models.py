from django.db import models
from django.conf import settings

class Position(models.Model):
    """
    Football positions taxonomy. Start simple with the line-based 4 buckets,
    evolve later to detailed roles (e.g., RB, RCB, LDM).
    """
    LINE_CHOICES = (
        ('GK', 'Goalkeeper'),
        ('DF', 'Defender'),
        ('MF', 'Midfielder'),
        ('FW', 'Forward'),
    )
    key = models.SlugField(max_length=32, unique=True)      # 'gk','df','mf','fw' or 'rb','lcb',...
    name = models.CharField(max_length=64)
    line = models.CharField(max_length=2, choices=LINE_CHOICES)

    class Meta:
        ordering = ['line', 'name']

    def __str__(self) -> str:
        return self.name


class Specialty(models.Model):
    key = models.SlugField(max_length=32, unique=True)      # 'fitness','analysis','gk-coach', ...
    name = models.CharField(max_length=64)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class License(models.Model):
    key = models.SlugField(max_length=32, unique=True)      # 'uefa-b','uefa-a','uefa-pro', ...
    name = models.CharField(max_length=64)
    issuer = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class PlayerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='player_profile')
    dob = models.DateField(null=True, blank=True)
    height_cm = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.PositiveIntegerField(null=True, blank=True)
    dominant_foot = models.CharField(max_length=8, null=True, blank=True)  # 'left','right','both'
    preferred_positions = models.ManyToManyField(Position, blank=True, related_name='players')
    bio = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"PlayerProfile<{self.user_id}>"


class CoachProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coach_profile')
    specialties = models.ManyToManyField(Specialty, blank=True, related_name='coaches')
    dob = models.DateField(null=True, blank=True)
    licenses = models.ManyToManyField(License, blank=True, related_name='coaches')
    years_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"CoachProfile<{self.user_id}>"


class StaffProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    specialties = models.ManyToManyField(Specialty, blank=True, related_name='staff')
    dob = models.DateField(null=True, blank=True)
    staff_type = models.CharField(max_length=64, blank=True)  # e.g. Physio, Analyst, Doctor, Kit Manager
    certifications = models.ManyToManyField(License, blank=True, related_name='staff')
    bio = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"StaffProfile<{self.user_id}>"
