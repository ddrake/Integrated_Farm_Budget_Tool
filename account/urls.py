from django.urls import path

from .views import (RegistrationView, ActivateView, CheckEmailView,
                    login, DeleteAccountView)

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('activate/<uidb64>/<token>/', ActivateView.as_view(), name='activate'),
    path('check-email/', CheckEmailView.as_view(), name="check_email"),
    path('login/', login, name='login'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),
]
