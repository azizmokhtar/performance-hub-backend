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
