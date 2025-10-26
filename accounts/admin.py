# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm
import csv
from django.http import HttpResponse

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ['username', 'email', 'role', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'role']

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

    # ✅ Add the export action
    actions = ["export_users_as_csv"]

    def export_users_as_csv(self, request, queryset):
        """
        Admin action to export selected CustomUser records as CSV.
        """
        if not queryset.exists():
            queryset = self.model.objects.all()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="users_report.csv"'
        writer = csv.writer(response)

        # Header row
        writer.writerow([
            "ID",
            "Username",
            "Email",
            "Role",
            "Is Staff",
            "Is Active",
            "Date Joined",
            "Last Login",
        ])

        # Data rows
        for user in queryset:
            writer.writerow([
                user.id,
                user.username,
                user.email,
                getattr(user, "role", ""),
                "Yes" if user.is_staff else "No",
                "Yes" if user.is_active else "No",
                user.date_joined.strftime("%Y-%m-%d %H:%M:%S") if user.date_joined else "",
                user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "",
            ])

        return response

    export_users_as_csv.short_description = "Export selected users as CSV"