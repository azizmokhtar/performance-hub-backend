from django.db import models
from django.conf import settings # To refer to AUTH_USER_MODEL

class DailyWellnessEntry(models.Model):
    SCORE_CHOICES = (
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    )

    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wellness_entries',
        limit_choices_to={'role': 'PLAYER'}
    )
    entry_date = models.DateField()
    sleep_quality = models.IntegerField(choices=SCORE_CHOICES)
    mood_score = models.IntegerField(choices=SCORE_CHOICES)
    soreness_score = models.IntegerField(choices=SCORE_CHOICES)
    fatigue_score = models.IntegerField(choices=SCORE_CHOICES, null=True, blank=True) # Can be calculated or self-reported
    injury_status = models.BooleanField(default=False)
    injury_description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'entry_date') # Ensures one entry per player per day
        ordering = ['-entry_date']
        verbose_name_plural = "Daily Wellness Entries"

    def __str__(self):
        return f"{self.player.get_full_name()} - Wellness on {self.entry_date}"