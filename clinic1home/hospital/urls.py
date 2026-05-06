from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),  # Make dashboard the home page
    path('book-appointment/', views.book_appointment, name='book_appointment'),

    path('patient/register/', views.register_patient, name='register_patient'),
    path('patient/revisit/', views.revisit_patient, name='revisit_patient'),
# hospital/urls.py
    path('patient/list/', views.patient_list, name='patient_list'),

path('patient/clerking/<str:op_number>/', views.clerking_patient, name='clerking_patient'),

    path('patient/clerking/', views.clerking_patient, name='clerking_patient'),

path('patient/card/<str:op_number>/', views.patient_card, name='patient_card'),

path('patient/card/<str:op_number>/pdf/', views.download_patient_card_pdf, name='download_patient_card_pdf'),

path('doctor/request/<str:op_number>/', views.doctor_request, name='doctor_request'),
path('payment/make/<str:bill_number>/', views.make_payment, name='make_payment'),

path('requests/', views.view_requests, name='view_requests'),
path('requests/<str:op_number>/', views.view_requests, name='view_requests_with_op'),

path('invoice/<str:bill_number>/', views.generate_invoice, name='generate_invoice'),

path('invoice/', views.view_invoice, name='view_invoice'),
path('invoice/<str:op_number>/', views.view_invoice, name='view_invoice_with_op'),

path('payment-history/', views.payment_history, name='payment_history'),
path('payment-history/pdf/', views.payment_history_pdf, name='payment_history_pdf'),

# Add to urls.py
path('financial-summary/', views.financial_summary, name='financial_summary'),

path('add-user/', views.add_user, name='add_user'),

path('change-password/', views.change_password, name='change_password'),

path('patient/<str:op_number>/', views.patient_detail, name='patient_detail'),
    path('patient/<str:op_number>/edit/', views.patient_edit, name='patient_edit'),

path('appointment/<str:appointment_number>/slip/', views.appointment_slip, name='appointment_slip'),

# Today's Appointments (create this view next)
path('appointments/today/', views.todays_appointments, name='todays_appointments'),

# All Appointments (full list)
path('appointments/all/', views.all_appointments, name='all_appointments'),


]