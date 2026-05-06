# hospital/admin.py
from django.contrib import admin
from .models import (
    Patient, Doctor, Department, Appointment, DiseaseCategory,
    ClinicalNote, Bill, LabRequest, Prescription, Payment,
    Drug, LabTest
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display  = ('op_number', 'full_name', 'phone', 'patient_type', 'registered_on')
    search_fields = ('op_number', 'full_name', 'phone', 'id_number')
    list_filter   = ('patient_type', 'payment_mode', 'registered_on', 'gender')
    readonly_fields = ('op_number', 'registered_on')
    ordering      = ('-registered_on',)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display  = ('name', 'specialization', 'department', 'phone')
    search_fields = ('name', 'specialization', 'phone')
    list_filter   = ('department',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ('name',)
    search_fields = ('name',)


@admin.register(DiseaseCategory)
class DiseaseCategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'is_chronic', 'typical_interval_days')
    list_filter   = ('is_chronic',)
    search_fields = ('name',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    # FIX: updated to match the new Appointment model fields (User FK, not Doctor FK)
    list_display  = ('appointment_number', 'patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
    list_filter   = ('status', 'appointment_date', 'disease_category')
    search_fields = ('appointment_number', 'patient__full_name', 'patient__op_number', 'doctor__username')
    readonly_fields = ('appointment_number', 'created_at')
    ordering      = ('-appointment_date',)


@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):
    list_display  = ('patient', 'doctor', 'clinic', 'clerked_on')
    search_fields = ('patient__full_name', 'patient__op_number', 'chief_complaint')
    list_filter   = ('clerked_on', 'clinic')
    readonly_fields = ('clerked_on',)


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display  = ('bill_number', 'patient', 'date', 'total_amount', 'paid_amount', 'balance', 'status')
    search_fields = ('bill_number', 'patient__full_name', 'patient__op_number')
    list_filter   = ('status', 'date')
    readonly_fields = ('bill_number', 'date', 'total_amount', 'paid_amount', 'balance')
    ordering      = ('-date',)


@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    list_display  = ('bill', 'lab_test', 'requested_by', 'requested_at', 'status')
    search_fields = ('bill__bill_number', 'lab_test__name')
    list_filter   = ('status', 'requested_at')


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display  = ('bill', 'drug', 'quantity', 'prescribed_by', 'prescribed_at', 'status')
    search_fields = ('bill__bill_number', 'drug__name')
    list_filter   = ('status', 'prescribed_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ('bill', 'amount_paid', 'method', 'paid_at', 'received_by')
    search_fields = ('bill__bill_number', 'transaction_ref', 'scheme_number')
    list_filter   = ('method', 'paid_at')
    readonly_fields = ('paid_at',)


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display  = ('name', 'price_per_unit', 'unit', 'is_active')
    search_fields = ('name', 'description')
    list_filter   = ('is_active', 'unit')
    ordering      = ('name',)


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display  = ('name', 'price', 'is_active')
    search_fields = ('name', 'description')
    list_filter   = ('is_active',)
    ordering      = ('name',)