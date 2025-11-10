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
