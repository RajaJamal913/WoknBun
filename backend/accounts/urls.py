from django.urls import path

from .auth_views import ChangePasswordView, LoginView, MeView, MyOrdersView, RefreshView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="customer-register"),
    path("auth/login/", LoginView.as_view(), name="customer-login"),
    path("auth/refresh/", RefreshView.as_view(), name="customer-refresh"),
    path("auth/me/", MeView.as_view(), name="customer-me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="customer-change-password"),
    path("auth/orders/", MyOrdersView.as_view(), name="customer-orders"),
]