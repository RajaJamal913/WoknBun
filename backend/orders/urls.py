from django.urls import path
from .views import OrderCreateView, ConfigView

urlpatterns = [
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("config/", ConfigView.as_view(), name="config"),
]
