from rest_framework import viewsets
from .models import Category, MenuItem, Deal
from .serializers import CategorySerializer, MenuItemSerializer, DealSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class MenuItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuItem.objects.filter(is_active=True).select_related("category").prefetch_related("prices")
    serializer_class = MenuItemSerializer


class DealViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Deal.objects.filter(is_active=True)
    serializer_class = DealSerializer
