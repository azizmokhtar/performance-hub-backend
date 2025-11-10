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
