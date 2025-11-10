from django.db import models
from django.conf import settings # To refer to AUTH_USER_MODEL

from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings  # AUTH_USER_MODEL
from django.db import models
from django.conf import settings
from profiles.models import Position
class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    club_crest = models.ImageField(upload_to='club_crests/', null=True, blank=True)

    head_coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coached_teams',
        limit_choices_to={'role': 'COACH'},  # UI-level filtering
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

    # ---- Validation: enforce head_coach is a COACH ----
    def clean(self):
        super().clean()
        if self.head_coach and getattr(self.head_coach, "role", None) != "COACH":
            raise ValidationError({"head_coach": "Selected user is not a COACH."})

    def save(self, *args, **kwargs):
        self.full_clean(exclude=None)
        return super().save(*args, **kwargs)

    def active_memberships(self, season: 'Season | None' = None):
        qs = self.memberships.filter(active=True)
        if season:
            qs = qs.filter(season=season)
        return qs.select_related('user', 'primary_position')

    def get_squad(self, season: 'Season | None' = None):
        return self.active_memberships(season).filter(role_on_team='PLAYER')

    def get_staff(self, season: 'Season | None' = None):
        return self.active_memberships(season).exclude(role_on_team='PLAYER')


class Season(models.Model):
    key = models.SlugField(max_length=32, unique=True)   # '2025-26'
    name = models.CharField(max_length=64)               # 'Season 2025/2026'
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            Season.objects.exclude(pk=self.pk).update(is_current=False)


class TeamMembership(models.Model):
    ROLE_CHOICES = (
        ('PLAYER', 'Player'),
        ('COACH', 'Coach'),
        ('STAFF', 'Staff'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='memberships')
    season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True, related_name='memberships')

    role_on_team = models.CharField(max_length=10, choices=ROLE_CHOICES)
    jersey_number = models.PositiveIntegerField(null=True, blank=True)
    primary_position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.SET_NULL, related_name='primary_memberships')
    secondary_positions = models.ManyToManyField(Position, blank=True, related_name='secondary_memberships')
    squad_status = models.CharField(max_length=32, blank=True)  # e.g., 'First Team', 'U23', 'Loan', 'Trialist'
    active = models.BooleanField(default=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['team', 'role_on_team', 'active']),
            models.Index(fields=['user', 'team']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['team', 'season', 'jersey_number'],
                                    name='uniq_team_season_jersey',
                                    condition=models.Q(jersey_number__isnull=False)),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.team_id} ({self.role_on_team})"
