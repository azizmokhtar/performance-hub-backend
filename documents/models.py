from django.db import models
from django.conf import settings # To refer to AUTH_USER_MODEL
from teams.models import Team # Assuming teams app is already defined

class Document(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/%Y/%m/%d/') # Organized by year/month/day
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Don't delete document if uploader leaves
        null=True, blank=True,
        related_name='uploaded_documents'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='team_documents' # Can be null if shared globally by admin, or specifically with players
    )
    shared_with_players = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='shared_documents',
        blank=True,
        limit_choices_to={'role': 'PLAYER'} # Only players can be explicitly shared with
    )
    description = models.TextField(null=True, blank=True)
    file_type = models.CharField(max_length=50, blank=True) # E.g., 'PDF', 'JPEG', 'MP4', 'DOCX'
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Automatically determine file_type from file extension
        if self.file and not self.file_type:
            name, extension = os.path.splitext(self.file.name)
            self.file_type = extension.lstrip('.').upper()
        super().save(*args, **kwargs)