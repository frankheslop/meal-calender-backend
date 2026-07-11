from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "email_verified",
        "timezone",
        "is_staff",
        "is_active",
    )
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Account Preferences",
            {
                "fields": (
                    "timezone",
                    "email_verified",
                )
            },
        ),
    )
