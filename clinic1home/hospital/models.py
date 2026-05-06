# hospital/models.py
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from datetime import date
from decimal import Decimal

# ==================== FIRST: MODELS THAT OTHERS DEPEND ON ====================

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ==================== REAL DRUGS & LAB TESTS (DATABASE DRIVEN) ====================

class Drug(models.Model):
    name = models.CharField(max_length=150, unique=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit = models.CharField(max_length=50, default="tablet", blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - KES {self.price_per_unit} / {self.unit}"

    class Meta:
        ordering = ['name']


class LabTest(models.Model):
    name = models.CharField(max_length=150, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - KES {self.price}"

    class Meta:
        ordering = ['name']


# ==================== NOW THE REST ====================

class Patient(models.Model):
    op_number = models.CharField(max_length=10, unique=True, editable=False, blank=True)
    full_name = models.CharField("Full Name", max_length=100)
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField("Date of Birth")
    phone_regex = RegexValidator(regex=r'^\+254\d{9}$', message="Phone must be +254 followed by 9 digits")
    phone = models.CharField(validators=[phone_regex], max_length=13, unique=True)
    id_number = models.CharField("ID Number", max_length=20, blank=True, null=True)
    address = models.CharField("Residence / Address", max_length=200)
    next_of_kin_name = models.CharField("Next of Kin Name", max_length=100)
    next_of_kin_phone = models.CharField("Next of Kin Phone", max_length=13, blank=True)

    PATIENT_TYPE = [('outpatient', 'Outpatient')]
    patient_type = models.CharField(max_length=20, choices=PATIENT_TYPE, default='outpatient')

    PAYMENT_MODE = [('cash', 'Cash'), ('insurance', 'Insurance'), ('other', 'Other')]
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE, default='cash')

    registered_on = models.DateTimeField(auto_now_add=True)

    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def save(self, *args, **kwargs):
        if not self.op_number:
            last = Patient.objects.all().order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.op_number = f"OP{num:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.op_number} - {self.full_name}"

    class Meta:
        ordering = ['-registered_on']


class Doctor(models.Model):
    name = models.CharField(max_length=100, default="Dr. Unknown")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    specialization = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"Dr. {self.name}"


class ClinicalNote(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='notes')
    clerked_on = models.DateTimeField(auto_now_add=True)
    doctor = models.CharField(max_length=100, blank=True)
    clinic = models.CharField(max_length=100, blank=True)
    chief_complaint = models.TextField("Chief Complaint / Reason for Visit")
    history = models.TextField("History of Present Illness", blank=True)
    examination = models.TextField("Physical Examination", blank=True)
    diagnosis = models.TextField("Diagnosis / Plan", blank=True)
    vital_signs = models.TextField("Vital Signs (BP, Temp, Pulse, etc.)", blank=True)

    def __str__(self):
        return f"Clerking - {self.patient.full_name} ({self.clerked_on.date()})"


class Bill(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    bill_number = models.CharField(max_length=30, unique=True, editable=False)
    date = models.DateField(default=date.today)

    registration_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=100.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    consultation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=500.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partial'),
        ('PAID', 'Paid'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')

    def save(self, *args, **kwargs):
        if not self.bill_number:
            last = Bill.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.bill_number = f"BILL-{date.today().strftime('%Y%m%d')}-{num:04d}"
        if self.pk is None:
            self.total_amount = self.registration_fee + self.consultation_fee
        super().save(*args, **kwargs)

    def update_totals(self):
        pres_total = sum(item.subtotal for item in self.prescriptions.all())
        lab_total = sum(
            req.lab_test.price for req in self.lab_requests.all()
            if req.lab_test and req.lab_test.price is not None
        ) or Decimal('0.00')

        self.total_amount = (
            self.registration_fee +
            self.consultation_fee +
            pres_total +
            lab_total
        )
        self.paid_amount = sum(
            payment.amount_paid for payment in self.payments.all()
        ) or Decimal('0.00')

        self.balance = self.total_amount - self.paid_amount

        if self.balance <= 0:
            self.status = 'PAID'
            self.prescriptions.filter(status='PRESCRIBED').update(status='PAID')
            self.lab_requests.filter(status='REQUESTED').update(status='PAID')
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'UNPAID'

        self.save(update_fields=['total_amount', 'paid_amount', 'balance', 'status'])

    def __str__(self):
        return self.bill_number

    class Meta:
        ordering = ['-date']
        verbose_name = "Bill"
        verbose_name_plural = "Bills"


class LabRequest(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='lab_requests')
    lab_test = models.ForeignKey(LabTest, on_delete=models.PROTECT, null=True, blank=True)
    notes = models.TextField(blank=True)
    requested_by = models.CharField(max_length=100, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('REQUESTED', 'Requested'),
            ('PAID', 'Paid'),
            ('COMPLETED', 'Completed'),
        ],
        default='REQUESTED'
    )

    def __str__(self):
        return f"{self.lab_test.name if self.lab_test else 'No test'} for {self.bill.patient.full_name}"


class Prescription(models.Model):
    bill = models.ForeignKey(
        'Bill',
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    drug = models.ForeignKey(
        'Drug',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='prescriptions'
    )
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    prescribed_by = models.CharField(max_length=100, blank=True)
    prescribed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PRESCRIBED', 'Prescribed'),
            ('PAID', 'Paid'),
            ('DISPENSED', 'Dispensed'),
        ],
        default='PRESCRIBED'
    )

    @property
    def subtotal(self):
        if self.drug and self.drug.price_per_unit is not None:
            return Decimal(self.quantity) * Decimal(self.drug.price_per_unit)
        return Decimal('0.00')

    def __str__(self):
        drug_name = self.drug.name if self.drug else 'No drug assigned'
        return f"{self.quantity} × {drug_name} for {self.bill.patient.full_name}"

    class Meta:
        ordering = ['-prescribed_at']
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"


class Payment(models.Model):
    METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('MPESA', 'Lipa na M-Pesa'),
        ('INSURANCE', 'Insurance / SHA'),
        ('BANK', 'Bank Transfer'),
        ('OTHER', 'Other'),
    ]

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    transaction_ref = models.CharField(max_length=100, blank=True)
    scheme_number = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    received_by = models.CharField(max_length=100, blank=True)

    # FIX: removed update_totals() from save() to prevent recursion.
    # update_totals() is called explicitly in the make_payment view instead.
    def __str__(self):
        return f"KES {self.amount_paid} - {self.method} - Bill {self.bill.bill_number}"


# ─── DISEASE CATEGORY ───────────────────────────────────────────────
class DiseaseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_chronic = models.BooleanField(default=False)
    typical_interval_days = models.IntegerField(default=30)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Disease Categories"


# ─── APPOINTMENT (single definition, uses User FK) ──────────────────
class Appointment(models.Model):
    appointment_number = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'groups__name__in': ['doctor', 'admin']}
    )
    disease_category = models.ForeignKey(DiseaseCategory, on_delete=models.SET_NULL, null=True)
    appointment_date = models.DateField(null=True, blank=True)
    appointment_time = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('booked', 'Booked'),
            ('confirmed', 'Confirmed'),
            ('attended', 'Attended'),
            ('cancelled', 'Cancelled'),
        ],
        default='booked'
    )
    email = models.EmailField("Patient Email for Reminder", blank=True, null=True)
    phone = models.CharField(max_length=13, blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_appointments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment_number} - {self.patient.full_name}"

    class Meta:
        ordering = ['appointment_date', 'appointment_time']