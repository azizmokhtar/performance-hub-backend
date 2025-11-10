Phase 1 — add the performance spine (sessions, attendance, wellness, loads)

These models give you immediate, scientifically useful data (wellness + sRPE) without hardware and unlock EWMA-ACWR.

New models (in a new app, e.g., performance/)
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

Why this matters (coach view)

WellnessLog gives the morning “red flags.”

SessionRPE gives internal training load.

DailyLoad enables fast ACWR queries.

LoadACWR stores EWMA acute/chronic per day (scientifically better than rolling averages), so dashboards are instant.

Signals / tasks to keep DailyLoad in sync
# performance/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import SessionRPE, DailyLoad

def _recompute_daily_internal_load(membership_id, date):
    qs = SessionRPE.objects.filter(membership_id=membership_id, session__start__date=date)
    total = sum(int(x.load_au) for x in qs)
    DailyLoad.objects.update_or_create(
        membership_id=membership_id, date=date,
        defaults={"internal_load_au": total}
    )

@receiver(post_save, sender=SessionRPE)
def on_srpe_save(sender, instance, created, **kwargs):
    _recompute_daily_internal_load(instance.membership_id, instance.session.start.date())

@receiver(post_delete, sender=SessionRPE)
def on_srpe_delete(sender, instance, **kwargs):
    _recompute_daily_internal_load(instance.membership_id, instance.session.start.date())

EWMA-ACWR computation (management command or Celery beat)

Choose λ (decay) for acute (e.g., half-life ~3–7 days) and chronic (e.g., half-life ~21–28 days).

Pseudocode:

# performance/acwr.py
import math
from datetime import date, timedelta
from .models import DailyLoad, LoadACWR

def ewma(prev, x_t, alpha):
    return alpha * x_t + (1 - alpha) * prev

def alpha_from_halflife(hl_days):
    return 1 - math.exp(math.log(0.5) / hl_days)

def compute_acwr_for_member(membership_id, start_date, end_date):
    a_alpha = alpha_from_halflife(7)   # acute half-life ~7d
    c_alpha = alpha_from_halflife(28)  # chronic half-life ~28d

    # Iterate dates; pull loads (missing -> 0)
    d = start_date
    acute = 0.0
    chronic = 0.0

    # warm-up: backfill some history if you have it (optional)

    while d <= end_date:
        dl = DailyLoad.objects.filter(membership_id=membership_id, date=d).first()
        x = (dl.internal_load_au if dl else 0)
        acute = ewma(acute, x, a_alpha)
        chronic = ewma(chronic, x, c_alpha)
        ratio = (acute / chronic) if chronic > 0 else 0.0

        LoadACWR.objects.update_or_create(
            membership_id=membership_id, date=d, source="INTERNAL",
            defaults=dict(acute_ewma=acute, chronic_ewma=chronic, ratio=ratio)
        )
        d += timedelta(days=1)


Run nightly (Celery beat) for all active memberships (or incrementally for “today”).

Minimal APIs (DRF)

POST /performance/sessions/ (coach) — create session.

POST /performance/sessions/{id}/attendance/ — bulk upsert attendance.

POST /performance/sessions/{id}/srpe/ (player or coach on behalf) — body {membership_id, rpe_0_10, duration_min}; server computes load_au.

POST /performance/wellness/ (player) — upsert daily.

GET /performance/members/{membership_id}/acwr/?from=YYYY-MM-DD&to=... — returns ratio timeseries + flags (>1.4 danger).

Permissions: players can only write their own wellness & own sRPE; coaches/admins can write for their team. Reuse your IsCoachOwnerMemberOrAdmin.

Phase 2 — external data ready (no vendor lock-in)

Add very light integration objects so you can ingest Whoop/Oura (HRV/sleep) and GPS later.

# performance/integrations.py (models)
class ExternalProvider(models.TextChoices):
    WHOOP = "WHOOP", "Whoop"
    OURA = "OURA", "Oura"
    CATAPULT = "CATAPULT", "Catapult"
    STATSPORTS = "STATSPORTS", "STATSports"
    VEO = "VEO", "Veo"

class LinkedDevice(models.Model):
    membership = models.ForeignKey('teams.TeamMembership', on_delete=models.CASCADE, related_name='devices')
    provider = models.CharField(max_length=16, choices=ExternalProvider.choices)
    external_user_id = models.CharField(max_length=128)
    access_token = models.CharField(max_length=512)  # store encrypted
    refresh_token = models.CharField(max_length=512, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DailyHRV(models.Model):
    membership = models.ForeignKey('teams.TeamMembership', on_delete=models.CASCADE, related_name='hrv_daily')
    date = models.DateField()
    rMSSD_ms = models.FloatField(null=True, blank=True)
    ln_rMSSD = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=16, choices=ExternalProvider.choices)

    class Meta:
        unique_together = [('membership','date','source')]
        indexes = [models.Index(fields=['membership','date'])]


This lets you add fatigue flags: “HRV 20% below 7-day baseline” → coach alert.

Phase 3 — API polishing & performance

Prefetch patterns in your squad/staff serializers are good. Keep doing:

Team.memberships.select_related('user','primary_position')

For list endpoints, annotate flags (e.g., latest acwr.ratio) so the roster view can show a red/amber/green dot per player without extra calls.

Example:

# teams/views.py (annotate latest ACWR ratio)
from django.db.models import Subquery, OuterRef, FloatField
from performance.models import LoadACWR

latest_ratio_sq = Subquery(
    LoadACWR.objects.filter(membership=OuterRef('pk'), source='INTERNAL')
    .order_by('-date')
    .values('ratio')[:1],
    output_field=FloatField()
)
qs = team.memberships.filter(active=True).select_related('user','primary_position').annotate(latest_acwr=latest_ratio_sq)


Then in your serializer, expose latest_acwr if present.

What changes for coaches & players (UX)

Players: Daily 20-second flow (wellness), post-session sRPE slider (0–10). No hardware needed.

Coaches:

Session planning in calendar (you already have calendar_events planned, wire it to TrainingSession).

Dashboard: red/amber/green fatigue (ACWR/EWMA), morning wellness flags, attendance discipline.

Export: weekly PDF/CSV for staff.