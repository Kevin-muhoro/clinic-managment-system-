# hospital/views.py
from decimal import Decimal

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.conf import settings
from django.forms import inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, DateField, ExpressionWrapper, DecimalField, F
from django.db.models.functions import TruncDay
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, date, timedelta

from xhtml2pdf import pisa
from django.template.loader import render_to_string
from dateutil.relativedelta import relativedelta

from .models import Patient, ClinicalNote, Bill, Prescription, LabRequest, Payment, Drug, LabTest, Appointment
from .forms import (
    PatientForm, ClinicalNoteForm, LabRequestForm, PrescriptionForm,
    PaymentForm, AppointmentBookingForm, UserCreationForm
)


# ── Appointment views ─────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def todays_appointments(request):
    today = timezone.now().date()
    appointments = Appointment.objects.filter(appointment_date=today).order_by('appointment_time')
    return render(request, 'todays_appointments.html', {
        'appointments': appointments,
        'today': today,
    })


@login_required(login_url='/login/')
def all_appointments(request):
    appointments = Appointment.objects.all().order_by('-appointment_date', 'appointment_time')
    return render(request, 'all_appointments.html', {
        'appointments': appointments,
    })


@login_required(login_url='/login/')
def appointment_slip(request, appointment_number):
    appointment = get_object_or_404(Appointment, appointment_number=appointment_number)
    return render(request, 'appointment_slip.html', {'appointment': appointment})


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_patients     = Patient.objects.count()
    new_patients_today = Patient.objects.filter(registered_on__date=today).count()

    monthly_revenue = Bill.objects.filter(
        date__gte=month_start, date__lte=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    pending_bills_count   = Bill.objects.filter(balance__gt=0).count()
    pending_lab_requests  = LabRequest.objects.filter(status='REQUESTED').count()
    pending_prescriptions = Prescription.objects.filter(status='PRESCRIBED').count()

    recent_patients = Patient.objects.order_by('-registered_on')[:5]

    monthly_labels        = []
    monthly_registrations = []
    for i in range(11, -1, -1):
        target_month   = today - relativedelta(months=i)
        month_start_day = target_month.replace(day=1)
        month_end_day   = (month_start_day + relativedelta(months=1)) - timedelta(days=1)
        count = Patient.objects.filter(registered_on__range=[month_start_day, month_end_day]).count()
        monthly_labels.append(target_month.strftime("%b %Y"))
        monthly_registrations.append(count)

    context = {
        'total_patients':        total_patients,
        'new_patients_today':    new_patients_today,
        'monthly_revenue':       monthly_revenue,
        'pending_bills_count':   pending_bills_count,
        'pending_lab_requests':  pending_lab_requests,
        'pending_prescriptions': pending_prescriptions,
        'recent_patients':       recent_patients,
        'monthly_labels':        monthly_labels,
        'monthly_registrations': monthly_registrations,
        'user_groups':           [g.name for g in request.user.groups.all()],
    }
    return render(request, 'dashboard.html', context)


# ── Patient views ─────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def register_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.save()
            messages.success(request, f"Patient '{patient.full_name}' (OP: {patient.op_number}) successfully registered!")
            return redirect('patient_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientForm()
    return render(request, 'register_patient.html', {'form': form})


@login_required(login_url='/login/')
def revisit_patient(request):
    query     = request.GET.get('q', '').strip()
    from_date = request.GET.get('from_date')
    to_date   = request.GET.get('to_date')

    patients = Patient.objects.all().order_by('-registered_on')

    if query:
        patients = patients.filter(
            Q(op_number__icontains=query) |
            Q(full_name__icontains=query) |
            Q(phone__icontains=query)
        )
    if from_date:
        patients = patients.filter(registered_on__date__gte=from_date)
    if to_date:
        patients = patients.filter(registered_on__date__lte=to_date)

    selected_op     = query if query and Patient.objects.filter(op_number__iexact=query).exists() else None
    selected_patient = Patient.objects.filter(op_number__iexact=selected_op).first() if selected_op else None

    return render(request, 'revisit_patient.html', {
        'patients':         patients,
        'selected_patient': selected_patient,
        'selected_op':      selected_op,
    })


@login_required(login_url='/login/')
def patient_list(request):
    query    = request.GET.get('q', '').strip()
    patients = Patient.objects.all().order_by('-registered_on')

    if query:
        patients = patients.filter(
            Q(op_number__icontains=query) |
            Q(full_name__icontains=query) |
            Q(phone__icontains=query)
        )

    return render(request, 'patient_list.html', {
        'patients':       patients,
        'query':          query,
        'total_patients': patients.count(),
    })


@login_required(login_url='/login/')
def patient_detail(request, op_number):
    patient = get_object_or_404(Patient, op_number=op_number)
    return render(request, 'patient_detail.html', {'patient': patient})


@login_required(login_url='/login/')
def patient_edit(request, op_number):
    patient = get_object_or_404(Patient, op_number=op_number)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f"Patient '{patient.full_name}' (OP: {patient.op_number}) successfully updated!")
            return redirect('patient_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patient_edit.html', {
        'form':    form,
        'patient': patient,
        'is_edit': True,
    })


@login_required(login_url='/login/')
def clerking_patient(request, op_number=None):
    query = request.GET.get('q', '').strip()

    if query and not op_number:
        patient = Patient.objects.filter(
            Q(op_number__iexact=query) |
            Q(full_name__icontains=query)
        ).first()
        if patient:
            return redirect('clerking_patient', op_number=patient.op_number)
        else:
            messages.error(request, f"No patient found with '{query}'")
            return redirect('clerking_patient')

    patient = None
    if op_number:
        patient = get_object_or_404(Patient, op_number=op_number)

    if request.method == 'POST' and patient:
        form = ClinicalNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.patient = patient
            note.doctor  = request.user.get_full_name() or request.user.username
            note.save()
            messages.success(request, f"Clerking saved successfully for {patient.full_name}!")
            return redirect('revisit_patient')
    else:
        form = ClinicalNoteForm()

    age = None
    if patient and patient.date_of_birth:
        today = date.today()
        age = today.year - patient.date_of_birth.year
        if (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
            age -= 1

    return render(request, 'clerking_patient.html', {
        'patient': patient,
        'form':    form,
        'today':   date.today(),
        'age':     age,
        'query':   query,
        'doctor':  request.user,
    })


@login_required(login_url='/login/')
def patient_card(request, op_number):
    patient = get_object_or_404(Patient, op_number=op_number)
    notes   = ClinicalNote.objects.filter(patient=patient).order_by('-clerked_on')
    bills   = Bill.objects.filter(patient=patient).order_by('-date')
    return render(request, 'patient_card.html', {
        'patient': patient,
        'notes':   notes,
        'bills':   bills,
    })


@login_required(login_url='/login/')
def download_patient_card_pdf(request, op_number):
    patient = get_object_or_404(Patient, op_number=op_number)
    notes   = ClinicalNote.objects.filter(patient=patient).order_by('-clerked_on')

    html_string = render_to_string('patient_card_pdf.html', {'patient': patient, 'notes': notes})
    response    = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Patient_Card_{op_number}.pdf"'
    pisa.CreatePDF(html_string, dest=response)
    return response


# ── Doctor request (prescriptions + lab) ─────────────────────────────────────

@login_required(login_url='/login/')
def doctor_request(request, op_number):
    patient = get_object_or_404(Patient, op_number=op_number)

    bill, created = Bill.objects.get_or_create(patient=patient, date=date.today())

    PrescriptionFormSet = inlineformset_factory(
        Bill, Prescription, form=PrescriptionForm,
        extra=1, can_delete=True, max_num=20
    )
    LabRequestFormSet = inlineformset_factory(
        Bill, LabRequest, form=LabRequestForm,
        extra=1, can_delete=True, max_num=20
    )

    pres_formset = PrescriptionFormSet(request.POST or None, instance=bill, prefix='pres')
    lab_formset  = LabRequestFormSet(request.POST or None,  instance=bill, prefix='lab')

    if request.method == 'POST':
        if pres_formset.is_valid() and lab_formset.is_valid():
            pres_formset.save()
            lab_formset.save()
            bill.update_totals()

            if bill.balance <= 0:
                messages.success(request, "Bill fully settled — all requests marked as PAID.")
            else:
                messages.success(
                    request,
                    f"Saved {bill.prescriptions.count()} prescription(s) and "
                    f"{bill.lab_requests.count()} lab request(s). "
                    f"Balance: KES {bill.balance:,.2f}"
                )

            pres_formset = PrescriptionFormSet(instance=bill, prefix='pres')
            lab_formset  = LabRequestFormSet(instance=bill,  prefix='lab')
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'doctor_request.html', {
        'patient':            patient,
        'pres_formset':       pres_formset,
        'lab_formset':        lab_formset,
        'saved_prescriptions': bill.prescriptions.all(),
        'saved_lab_requests':  bill.lab_requests.all(),
        'bill':               bill,
        'drugs':              Drug.objects.filter(is_active=True).order_by('name'),
        'lab_tests':          LabTest.objects.filter(is_active=True).order_by('name'),
    })


# ── Payment ───────────────────────────────────────────────────────────────────

# Methods that MUST be paid in full — no partial balance allowed
FULL_PAYMENT_METHODS = {'CASH', 'MPESA'}


@login_required(login_url='/login/')
def make_payment(request, bill_number):
    bill = get_object_or_404(Bill, bill_number=bill_number)
    form = PaymentForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            # ── Step 1: Save editable fees first so total is accurate ──────────
            reg_fee  = request.POST.get('registration_fee')
            cons_fee = request.POST.get('consultation_fee')
            if reg_fee:
                bill.registration_fee = Decimal(reg_fee)
            if cons_fee:
                bill.consultation_fee = Decimal(cons_fee)
            bill.save(update_fields=['registration_fee', 'consultation_fee'])

            # Recalculate the current total so we compare against the right figure
            bill.update_totals()
            bill.refresh_from_db()

            amount_paid = form.cleaned_data['amount_paid']
            method      = form.cleaned_data['method']

            # ── Step 2: Enforce full payment for CASH and MPESA ───────────────
            if method in FULL_PAYMENT_METHODS and amount_paid < bill.balance:
                form.add_error(
                    'amount_paid',
                    f"Cash and M-Pesa payments must cover the full balance. "
                    f"Please pay KES {bill.balance:,.2f} in full."
                )
                return render(request, 'make_payment.html', {'bill': bill, 'form': form})

            # ── Step 3: Save payment ──────────────────────────────────────────
            payment            = form.save(commit=False)
            payment.bill       = bill
            payment.received_by = request.user.get_full_name() or request.user.username
            payment.save()

            # ── Step 4: Recalculate totals after payment saved ────────────────
            bill.update_totals()

            messages.success(
                request,
                f"Payment of KES {payment.amount_paid:,.2f} via {payment.get_method_display()} "
                f"recorded successfully. Bill is now fully settled."
            )
            return redirect('view_requests_with_op', op_number=bill.patient.op_number)

    return render(request, 'make_payment.html', {'bill': bill, 'form': form})


# ── View requests ─────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def view_requests(request, op_number=None):
    patient      = None
    bills        = []
    pending_lab  = []
    paid_lab     = []
    pending_pres = []
    paid_pres    = []
    latest_bill  = None
    error_message = None

    # Support both URL kwarg (/requests/OP00001/) and query string (?op_number=OP00001)
    if not op_number:
        op_number = request.GET.get('op_number', '').strip()

    if op_number:
        try:
            patient      = Patient.objects.get(op_number__iexact=op_number)
            bills        = Bill.objects.filter(patient=patient).order_by('-date')
            pending_lab  = LabRequest.objects.filter(bill__patient=patient, status='REQUESTED').order_by('-requested_at')
            paid_lab     = LabRequest.objects.filter(bill__patient=patient, status='PAID').order_by('-requested_at')
            pending_pres = Prescription.objects.filter(bill__patient=patient, status='PRESCRIBED').order_by('-prescribed_at')
            paid_pres    = Prescription.objects.filter(bill__patient=patient, status='PAID').order_by('-prescribed_at')
            latest_bill  = bills.first() if bills.exists() else None
        except Patient.DoesNotExist:
            error_message = f"No patient found with OP number '{op_number}'. Please try again."
            op_number = ''

    return render(request, 'view_requests.html', {
        'patient':      patient,
        'bills':        bills,
        'pending_lab':  pending_lab,
        'paid_lab':     paid_lab,
        'pending_pres': pending_pres,
        'paid_pres':    paid_pres,
        'bill':         latest_bill,
        'search_op':    op_number,
        'error_message': error_message,
    })


# ── Invoice ───────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def generate_invoice(request, bill_number):
    bill    = get_object_or_404(Bill, bill_number=bill_number)
    patient = bill.patient

    context = {
        'bill':          bill,
        'patient':       patient,
        'prescriptions': Prescription.objects.filter(bill=bill),
        'lab_requests':  LabRequest.objects.filter(bill=bill),
        'payments':      Payment.objects.filter(bill=bill).order_by('-paid_at'),
        'today':         date.today(),
        'clinic_name':   "Hospital Pro",
        'clinic_address': "Meru, Kenya",
        'clinic_phone':  "+254 705 369 839",
    }

    html_string = render_to_string('invoice_pdf.html', context)
    response    = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{bill.bill_number}_{patient.op_number}.pdf"'
    pisa.CreatePDF(html_string, dest=response, encoding='utf-8')
    return response


@login_required(login_url='/login/')
def view_invoice(request):
    patient       = None
    bill          = None
    error_message = None

    op_number = request.GET.get('op_number', '').strip()
    if op_number:
        try:
            patient = Patient.objects.get(op_number__iexact=op_number)
            bill    = Bill.objects.filter(patient=patient).order_by('-date').first()
            if not bill:
                error_message = f"No bills found for patient {patient.full_name} ({patient.op_number}) yet."
        except Patient.DoesNotExist:
            error_message = f"No patient found with OP number '{op_number}'."
            op_number = ''

    return render(request, 'view_invoice.html', {
        'patient':       patient,
        'bill':          bill,
        'search_op':     request.GET.get('op_number', ''),
        'error_message': error_message,
    })


# ── Payment history ───────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def payment_history(request):
    payments         = Payment.objects.none()
    start_date       = None
    end_date         = None
    search_performed = False

    start = request.GET.get('start_date')
    end   = request.GET.get('end_date')

    if start and end:
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date   = datetime.strptime(end,   '%Y-%m-%d').date()
            payments   = Payment.objects.filter(
                paid_at__date__range=[start_date, end_date]
            ).select_related('bill__patient').order_by('-paid_at')
            search_performed = True
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")

    return render(request, 'payment_history.html', {
        'payments':         payments,
        'start_date':       start_date,
        'end_date':         end_date,
        'search_performed': search_performed,
        'total_amount':     payments.aggregate(total=Sum('amount_paid'))['total'] or 0,
    })


@login_required(login_url='/login/')
def payment_history_pdf(request):
    payments   = Payment.objects.none()
    start_date = None
    end_date   = None

    start = request.GET.get('start_date')
    end   = request.GET.get('end_date')

    if start and end:
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date   = datetime.strptime(end,   '%Y-%m-%d').date()
            payments   = Payment.objects.filter(
                paid_at__date__range=[start_date, end_date]
            ).select_related('bill__patient').order_by('-paid_at')
        except ValueError:
            return HttpResponse("Invalid date format", status=400)

    context = {
        'payments':     payments,
        'start_date':   start_date,
        'end_date':     end_date,
        'today':        datetime.now().date(),
        'clinic_name':  "Hospital Pro",
        'total_amount': payments.aggregate(total=Sum('amount_paid'))['total'] or 0,
    }

    html_string = render_to_string('payment_history_pdf.html', context)
    response    = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Payment_History_{}_to_{}.pdf"'.format(
        start_date or 'all', end_date or 'all'
    )
    pisa.CreatePDF(html_string, dest=response)
    return response


# ── Financial summary ─────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def financial_summary(request):
    end_date   = date.today()
    start_date = end_date - timedelta(days=30)

    # ── Only count revenue from fully PAID bills ──────────────────────────────
    paid_bills = Bill.objects.filter(status='PAID')

    total_drugs = Prescription.objects.filter(bill__status='PAID').aggregate(
        total=Sum(
            ExpressionWrapper(
                F('quantity') * F('drug__price_per_unit'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
    )['total'] or Decimal('0.00')

    total_tests        = LabRequest.objects.filter(bill__status='PAID').aggregate(
        total=Sum('lab_test__price')
    )['total'] or Decimal('0.00')

    total_consultation = paid_bills.aggregate(total=Sum('consultation_fee'))['total'] or Decimal('0.00')
    total_registration = paid_bills.aggregate(total=Sum('registration_fee'))['total'] or Decimal('0.00')

    # Grand total = sum of all actual payments received (most accurate)
    grand_total = Payment.objects.filter(
        bill__status='PAID'
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    # Daily breakdown — only PAID bills in the selected date range
    daily_data = Bill.objects.filter(
        date__range=[start_date, end_date],
        status='PAID'
    ).annotate(
        day=TruncDay('date')
    ).values('day').annotate(
        drugs=Sum(
            ExpressionWrapper(
                F('prescriptions__quantity') * F('prescriptions__drug__price_per_unit'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ),
        tests=Sum('lab_requests__lab_test__price'),
        consultation=Sum('consultation_fee'),
        registration=Sum('registration_fee'),
        daily_total=Sum('total_amount')
    ).order_by('day')

    return render(request, 'financial_summary.html', {
        'total_drugs':        total_drugs,
        'total_tests':        total_tests,
        'total_consultation': total_consultation,
        'total_registration': total_registration,
        'grand_total':        grand_total,
        'daily_data':         list(daily_data),
        'breakdown': {
            'Drugs':        float(total_drugs),
            'Tests':        float(total_tests),
            'Consultation': float(total_consultation),
            'Registration': float(total_registration),
        },
        'start_date': start_date,
        'end_date':   end_date,
    })


# ── User management ───────────────────────────────────────────────────────────

def is_admin(user):
    return user.groups.filter(name='admin').exists() or user.is_superuser


@login_required(login_url='/login/')
@user_passes_test(is_admin, login_url='/login/')
def add_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user      = form.save()
            role_name = form.cleaned_data['role'].name
            full_name = user.get_full_name() or 'no name'
            messages.success(
                request,
                f"New user '{user.username}' ({full_name}) created with role: {role_name}."
            )
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'add_user.html', {'form': form})


@login_required(login_url='/login/')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been successfully updated!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})


# ── Book appointment + email helpers ──────────────────────────────────────────

@login_required(login_url='/login/')
def book_appointment(request):
    """Book a new appointment and send email reminders."""
    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            appointment            = form.save(commit=False)
            appointment.doctor     = request.user
            appointment.created_by = request.user
            # FIX: do NOT override appointment_date here — the form scheduler already set it
            appointment.save()

            send_patient_reminder(appointment)
            send_doctor_notification(appointment)

            messages.success(
                request,
                f'Appointment {appointment.appointment_number} booked successfully! '
                f'Confirmation emails have been sent.'
            )
            return redirect('appointment_slip', appointment_number=appointment.appointment_number)
    else:
        form = AppointmentBookingForm()

    return render(request, 'book_appointment.html', {'form': form})


def send_patient_reminder(appointment):
    """Send a booking confirmation email to the patient."""
    recipient = appointment.email
    if not recipient:
        print(f"[EMAIL] No patient email for {appointment.appointment_number} — skipping.")
        return

    patient_name = appointment.patient.full_name
    doctor_name  = appointment.doctor.get_full_name() or appointment.doctor.username
    appt_number  = appointment.appointment_number
    appt_date    = appointment.appointment_date.strftime('%d %B %Y') if appointment.appointment_date else 'TBC'
    category     = appointment.disease_category if appointment.disease_category else 'General'

    try:
        send_mail(
            subject=f"Appointment Confirmation – {appt_number}",
            message=(
                f"Dear {patient_name},\n\n"
                f"Your appointment has been booked successfully.\n\n"
                f"  Appointment No : {appt_number}\n"
                f"  Date           : {appt_date}\n"
                f"  Category       : {category}\n"
                f"  Doctor         : Dr. {doctor_name}\n\n"
                f"Please arrive 10–15 minutes before your scheduled time.\n\n"
                f"Regards,\nClinic Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        print(f"[EMAIL] Patient confirmation sent to {recipient} for {appt_number}.")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send patient email for {appt_number}: {e}")


def send_doctor_notification(appointment):
    """Send a new-appointment notification email to the assigned doctor."""
    recipient = appointment.doctor.email
    if not recipient:
        print(f"[EMAIL] Doctor has no email — skipping for {appointment.appointment_number}.")
        return

    doctor_name  = appointment.doctor.get_full_name() or appointment.doctor.username
    patient_name = appointment.patient.full_name
    op_number    = appointment.patient.op_number
    appt_number  = appointment.appointment_number
    appt_date    = appointment.appointment_date.strftime('%d %B %Y') if appointment.appointment_date else 'TBC'
    category     = appointment.disease_category if appointment.disease_category else 'General'
    contact      = appointment.email or appointment.phone or 'Not provided'

    try:
        send_mail(
            subject=f"New Appointment – {appt_number} | {patient_name}",
            message=(
                f"Dear Dr. {doctor_name},\n\n"
                f"A new appointment has been booked and assigned to you.\n\n"
                f"  Appointment No : {appt_number}\n"
                f"  Patient        : {patient_name} (OP: {op_number})\n"
                f"  Date           : {appt_date}\n"
                f"  Category       : {category}\n"
                f"  Patient Contact: {contact}\n\n"
                f"Please log in to the system to view full details.\n\n"
                f"Regards,\nClinic System"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=True,
        )
        print(f"[EMAIL] Doctor notification sent to {recipient} for {appt_number}.")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send doctor notification for {appt_number}: {e}")