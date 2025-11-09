from django.db import models
from django.conf import settings # To refer to AUTH_USER_MODEL

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    club_crest = models.ImageField(upload_to='club_crests/', null=True, blank=True)
    head_coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coached_teams',
        limit_choices_to={'role': 'COACH'} # Restrict to users with 'COACH' role
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='owned_teams'
    )
    established_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_squad(self):
        return self.members.filter(role='PLAYER') # 'members' is the related_name from CustomUser.team

    def get_staff(self):
        return self.members.exclude(role='PLAYER')