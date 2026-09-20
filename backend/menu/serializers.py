from rest_framework import serializers
from .models import Category, MenuItem, MenuItemPrice, Deal


class MenuItemPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItemPrice
        fields = ["id", "label", "price"]


class MenuItemSerializer(serializers.ModelSerializer):
    prices = MenuItemPriceSerializer(many=True, read_only=True)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            "id", "category", "name", "description", "note",
            "image_url", "badge", "prices",
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "order"]


class DealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
        fields = ["id", "name", "description", "price", "badge", "image_url"]
