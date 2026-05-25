"""URL routing principal."""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

def admin_logout_redirect(request):
    """Custom logout that redirects to login page."""
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect(reverse_lazy('admin:login'))

urlpatterns = [
    path('admin/logout/', admin_logout_redirect, name='admin_logout'),
    path('admin/', admin.site.urls),
    path('', include('factures.urls')),
]
