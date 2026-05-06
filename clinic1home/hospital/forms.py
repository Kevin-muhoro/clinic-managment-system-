# hospital/forms.py
from datetime import date, time, timedelta

from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Patient, ClinicalNote, LabRequest, Prescription, Payment, Bill, Appointment


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'full_name', 'gender', 'date_of_birth', 'phone', 'id_number', 'address',
            'next_of_kin_name', 'next_of_kin_phone', 'patient_type', 'payment_mode'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'John kamau'}),
            'gender': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date', 'max': '9999-12-31'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': '712345678',
                'maxlength': '9',
                'inputmode': 'numeric',
            }),
            'id_number': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '12345678 (adults 18+ only)'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Street, City, Estate'}),
            'next_of_kin_name': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Jane wangui'}),
            'next_of_kin_phone': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'maxlength': '9',
                'placeholder': '712345678 (optional)',
                'inputmode': 'numeric',
            }),
            'patient_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'payment_mode': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set max to today so the browser date-picker blocks future dates
        self.fields['date_of_birth'].widget.attrs['max'] = date.today().isoformat()

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if not dob:
            raise forms.ValidationError("Date of birth is required.")
        today = date.today()
        if dob >= today:
            raise forms.ValidationError(
                "Date of birth cannot be today or in the future. "
                "Please enter a valid date of birth."
            )
        # Sanity check — no one is older than 150 years
        if (today.year - dob.year) > 150:
            raise forms.ValidationError("Please enter a valid date of birth.")
        return dob

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if phone.isdigit() and len(phone) == 9:
            phone = '+254' + phone
        elif phone.startswith('0') and len(phone) == 10:
            phone = '+254' + phone[1:]
        elif phone.startswith('+254') and len(phone) == 13:
            pass
        else:
            raise forms.ValidationError("Enter exactly 9 digits (e.g. 712345678)")
        if not phone[4:].isdigit():
            raise forms.ValidationError("Phone digits must be numeric.")
        return phone

    def clean_next_of_kin_phone(self):
        phone = self.cleaned_data.get('next_of_kin_phone', '').strip()
        # FIX: if empty, return empty string immediately (not None)
        if not phone:
            return ''
        if phone.isdigit() and len(phone) == 9:
            phone = '+254' + phone
        elif phone.startswith('0') and len(phone) == 10:
            phone = '+254' + phone[1:]
        elif phone.startswith('+254') and len(phone) == 13:
            pass
        else:
            raise forms.ValidationError("Enter exactly 9 digits (e.g. 712345678)")
        if not phone[4:].isdigit():
            raise forms.ValidationError("Phone digits must be numeric.")
        return phone

    def clean_id_number(self):
        id_number = (self.cleaned_data.get('id_number') or '').strip()
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            today = date.today()
            age = today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )
            if age >= 18:
                if not id_number:
                    raise forms.ValidationError("ID Number is required for patients aged 18 and above.")
                if len(id_number) < 6 or not id_number.isalnum():
                    raise forms.ValidationError("ID Number must be at least 6 alphanumeric characters.")
                if Patient.objects.filter(id_number=id_number).exclude(pk=self.instance.pk).exists():
                    raise forms.ValidationError("This ID Number is already registered to another patient.")
        return id_number


class ClinicalNoteForm(forms.ModelForm):
    class Meta:
        model = ClinicalNote
        fields = [
            'clinic', 'chief_complaint', 'history', 'examination',
            'diagnosis', 'vital_signs'
        ]
        widgets = {
            'chief_complaint': forms.Textarea(attrs={'rows': 3}),
            'history': forms.Textarea(attrs={'rows': 6}),
            'examination': forms.Textarea(attrs={'rows': 6}),
            'diagnosis': forms.Textarea(attrs={'rows': 5}),
            'vital_signs': forms.Textarea(attrs={'rows': 4, 'placeholder': 'BP: 120/80, Temp: 36.5°C, Pulse: 80, etc.'}),
        }


class LabRequestForm(forms.ModelForm):
    class Meta:
        model = LabRequest
        fields = ['lab_test', 'notes']
        widgets = {
            'lab_test': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['drug', 'quantity', 'notes']
        widgets = {
            'drug': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'min': 1, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount_paid', 'method', 'transaction_ref', 'scheme_number']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'KES 0.00',
                'step': '0.01',
                'min': '0',
            }),
            'method': forms.Select(attrs={'class': 'form-select', 'id': 'payment-method'}),
            'transaction_ref': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'M-Pesa Code'}),
            'scheme_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CR / Claim Ref'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheme_number'].required  = False
        self.fields['transaction_ref'].required = False


# Formset for multiple prescriptions (drugs)
PrescriptionFormSet = inlineformset_factory(
    Bill, Prescription,
    form=PrescriptionForm,
    extra=1,
    can_delete=True,
)

# Formset for multiple lab requests
LabRequestFormSet = inlineformset_factory(
    Bill, LabRequest,
    form=LabRequestForm,
    extra=1,
    can_delete=True,
)


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)
    role = forms.ModelChoiceField(queryset=Group.objects.all(), label="Role")

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            role = self.cleaned_data["role"]
            user.groups.clear()
            user.groups.add(role)
        return user


# ── Scheduling helpers ────────────────────────────────────────────────────────

WORKING_DAYS     = {0, 1, 2, 3, 4}   # Mon–Fri
ACUTE_DAYS_AHEAD = 1                  # Urgent: next working day
CHRONIC_DAYS_AHEAD = 7                # Follow-up: ~1 week out
ACUTE_TIME       = time(8,  0)        # 08:00
CHRONIC_TIME     = time(10, 0)        # 10:00


def _next_working_day(from_date: date, days_ahead: int) -> date:
    """Add days_ahead then skip past any weekend."""
    candidate = from_date + timedelta(days=days_ahead)
    while candidate.weekday() not in WORKING_DAYS:
        candidate += timedelta(days=1)
    return candidate


def get_appointment_schedule(disease_category, booked_on: date = None):
    """
    Return (appointment_date, appointment_time) based on disease category.
    - Acute  (is_chronic=False) → +1 working day,  08:00
    - Chronic (is_chronic=True) → typical_interval_days working days, 10:00
    """
    if booked_on is None:
        booked_on = date.today()

    is_chronic = getattr(disease_category, 'is_chronic', False)
    interval   = getattr(disease_category, 'typical_interval_days', None)

    if not interval or interval <= 0:
        interval = CHRONIC_DAYS_AHEAD if is_chronic else ACUTE_DAYS_AHEAD

    appt_date = _next_working_day(booked_on, interval)
    appt_time = CHRONIC_TIME if is_chronic else ACUTE_TIME

    return appt_date, appt_time


class AppointmentBookingForm(forms.ModelForm):
    op_number = forms.CharField(
        max_length=10,
        label="Patient OP Number",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. OP00001',
            'autocomplete': 'off',
        })
    )

    class Meta:
        model  = Appointment
        fields = ['disease_category', 'email', 'phone']
        widgets = {
            'disease_category': forms.Select(),
            'email': forms.EmailInput(attrs={'placeholder': 'patient@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '712345678'}),
        }

    def clean_op_number(self):
        op_number = self.cleaned_data['op_number'].strip().upper()
        try:
            self._patient = Patient.objects.get(op_number=op_number)
        except Patient.DoesNotExist:
            raise ValidationError(f'No patient found with OP Number "{op_number}".')
        return op_number

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('email') and not cleaned_data.get('phone'):
            raise ValidationError(
                'Please provide at least an email or phone number for appointment reminders.'
            )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.patient = self._patient

        # Auto-schedule date + time from disease category
        if instance.disease_category:
            appt_date, appt_time = get_appointment_schedule(
                disease_category=instance.disease_category,
                booked_on=date.today(),
            )
            instance.appointment_date = appt_date
            instance.appointment_time = appt_time
        else:
            instance.appointment_date = date.today()
            instance.appointment_time = ACUTE_TIME

        instance.appointment_number = self._generate_appointment_number()

        if commit:
            instance.save()
        return instance

    @staticmethod
    def _generate_appointment_number():
        last = Appointment.objects.order_by('-id').first()
        num  = (last.id + 1) if last else 1
        return f"AP{timezone.now().strftime('%Y%m%d')}-{num:04d}"