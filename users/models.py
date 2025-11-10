# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.functions import Lower
from .managers import CustomUserManager

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('PLAYER', 'Player'),
        ('COACH', 'Coach'),
        ('STAFF', 'Staff'),
        ('ADMIN', 'Admin'),
    )

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='PLAYER')
    # DEPRECATED FIELDS REMOVED:
    # team = ...
    # date_of_birth = ...
    # jersey_number = ...
    # position = ...
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

    objects = CustomUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower('email'), name='uniq_customuser_email_ci')
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def is_player(self): return self.role == 'PLAYER'
    def is_coach(self): return self.role == 'COACH'
    def is_staff_member(self): return self.role == 'STAFF'
    def is_admin(self): return self.role == 'ADMIN' or self.is_superuser  # ← fixed
