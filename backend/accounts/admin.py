from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "mobile_number", "gender", "created_at")
    search_fields = ("full_name", "email", "mobile_number")
    readonly_fields = ("auth_token", "created_at")