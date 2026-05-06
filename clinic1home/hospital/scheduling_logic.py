from datetime import date, time, timedelta


# ── Scheduling constants ───────────────────────────────────────────────────────

WORKING_DAYS   = {0, 1, 2, 3, 4}   # Mon=0 … Fri=4  (Sat=5, Sun=6 excluded)
CLINIC_OPEN    = time(8,  0)        # 08:00
CLINIC_CLOSE   = time(17, 0)        # 17:00

# Days ahead to schedule from booking date
ACUTE_DAYS_AHEAD   = 1   # Urgent: next working day
CHRONIC_DAYS_AHEAD = 7   # Follow-up: ~1 week out

# Default time slots per urgency type
ACUTE_TIME   = time(8,  0)   # 08:00 — first slot, urgent
CHRONIC_TIME = time(10, 0)   # 10:00 — mid-morning follow-up


def next_working_day(from_date: date, days_ahead: int) -> date:
    """
    Add `days_ahead` to `from_date`, then advance forward
    until we land on a weekday (Mon–Fri).
    """
    candidate = from_date + timedelta(days=days_ahead)
    while candidate.weekday() not in WORKING_DAYS:
        candidate += timedelta(days=1)
    return candidate


def get_appointment_schedule(disease_category, booked_on: date = None):
    """
    Given a DiseaseCategory object and the booking date,
    return (appointment_date, appointment_time).

    Rules:
      - Acute  (is_chronic=False) → +1 working day, 08:00
      - Chronic (is_chronic=True) → +7 working days, 10:00

    If the category has its own `typical_interval_days` set,
    that overrides the defaults above.
    """
    if booked_on is None:
        booked_on = date.today()

    is_chronic = getattr(disease_category, 'is_chronic', False)

    # Use the model's own interval if set, else fall back to our defaults
    interval = getattr(disease_category, 'typical_interval_days', None)
    if not interval or interval <= 0:
        interval = CHRONIC_DAYS_AHEAD if is_chronic else ACUTE_DAYS_AHEAD

    appt_date = next_working_day(booked_on, interval)
    appt_time = CHRONIC_TIME if is_chronic else ACUTE_TIME

    return appt_date, appt_time


# ─────────────────────────────────────────────────────────────────────────────
# HOW TO USE IN YOUR FORM save() METHOD
# Replace your existing save() with this:
# ─────────────────────────────────────────────────────────────────────────────

"""
    def save(self, commit=True):
        instance = super().save(commit=False)

        # Attach the looked-up patient
        instance.patient = self._patient

        # ✅ Auto-schedule date and time based on disease category
        appt_date, appt_time = get_appointment_schedule(
            disease_category=instance.disease_category,
            booked_on=date.today(),
        )
        instance.appointment_date = appt_date
        instance.appointment_time = appt_time

        # Generate appointment number
        instance.appointment_number = self._generate_appointment_number()

        if commit:
            instance.save()
        return instance
"""


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLES — what the scheduler produces
# ─────────────────────────────────────────────────────────────────────────────

"""
Booked on Wednesday 19 March 2026:

  Upper Respiratory Infections (acute, is_chronic=False)
    → +1 day = Thu 20 March 2026, 08:00

  Malaria (acute, is_chronic=False)
    → +1 day = Thu 20 March 2026, 08:00

  Diarrheal Diseases (acute, is_chronic=False)
    → +1 day = Thu 20 March 2026, 08:00

  Hypertension (chronic, is_chronic=True, typical_interval_days=30)
    → +30 days = Fri 17 April 2026 (skip if weekend → next Mon), 10:00

  Diabetes Mellitus (chronic, is_chronic=True, typical_interval_days=90)
    → +90 days = Mon 22 June 2026, 10:00

  Booked on Friday 20 March 2026 (acute):
    → +1 day = Sat 21 March → SKIP → Mon 23 March 2026, 08:00
"""