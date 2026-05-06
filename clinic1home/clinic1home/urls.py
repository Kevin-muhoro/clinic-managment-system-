from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

from hospital import views


# Root ALWAYS goes to login (no exception)
def force_login_root(request):
    return redirect('login')

urlpatterns = [
    # Root URL — always to login (even if already logged in)
    path('', force_login_root, name='home'),

    # Login page (standalone)
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),

    # Logout — back to login
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),

    # Admin (optional)
    path('admin/', admin.site.urls),

    # Your app URLs (protected by @login_required in views)
    path('', include('hospital.urls')),

    # Dashboard (only reachable after login)
    path('dashboard/', views.dashboard, name='dashboard'),
    # ... other paths ...
]