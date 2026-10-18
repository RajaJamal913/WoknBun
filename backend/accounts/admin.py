from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email", "has_account", "created_at")
    search_fields = ("full_name", "phone", "email")
    readonly_fields = ("created_at", "account_created_at", "last_login_at")
    exclude = ("password",)  # the hashed password is never shown or editable here

    @admin.display(boolean=True, description="Website account")
    def has_account(self, obj):
        return obj.has_account