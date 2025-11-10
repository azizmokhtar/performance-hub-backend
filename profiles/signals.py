from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from users.models import CustomUser
from .models import PlayerProfile, CoachProfile, StaffProfile

def _ensure_profile_for_role(user: CustomUser):
    """
    Create the correct profile for the current role if missing.
    Do not delete other profiles here—this is called both on create and after role-change cleanup.
    """
    if user.role == 'PLAYER':
        PlayerProfile.objects.get_or_create(user=user)
    elif user.role == 'COACH':
        CoachProfile.objects.get_or_create(user=user)
    elif user.role == 'STAFF':
        StaffProfile.objects.get_or_create(user=user)
    # ADMIN: no specialized profile by default

@receiver(pre_save, sender=CustomUser)
def _handle_role_change_cleanup(sender, instance: CustomUser, **kwargs):
    """
    If role is changing, delete incompatible profiles so a user doesn't carry wrong profile type.
    """
    if not instance.pk:
        return  # new user, nothing to compare
    try:
        prev = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if prev.role == instance.role:
        return

    # Role changed: remove old specialized profiles
    if prev.role == 'PLAYER':
        PlayerProfile.objects.filter(user=instance).delete()
    elif prev.role == 'COACH':
        CoachProfile.objects.filter(user=instance).delete()
    elif prev.role == 'STAFF':
        StaffProfile.objects.filter(user=instance).delete()
    # If prev was ADMIN, nothing to delete

@receiver(post_save, sender=CustomUser)
def _auto_create_profile_on_user_create(sender, instance: CustomUser, created, **kwargs):
    if created:
        _ensure_profile_for_role(instance)
    else:
        # Post role-change, make sure the correct profile exists
        _ensure_profile_for_role(instance)
