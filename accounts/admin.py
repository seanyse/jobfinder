# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, SavedCandidateSearch, SearchMatchNotification
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


@admin.register(SavedCandidateSearch)
class SavedCandidateSearchAdmin(admin.ModelAdmin):
    list_display = ['name', 'recruiter', 'is_active', 'match_count_display', 'new_match_count_display', 'created_at', 'last_checked']
    list_filter = ['is_active', 'created_at', 'match_all_skills']
    search_fields = ['name', 'recruiter__username', 'location', 'project_keyword']
    readonly_fields = ['created_at', 'updated_at', 'last_checked']
    filter_horizontal = ['skills']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('recruiter', 'name', 'is_active')
        }),
        ('Search Criteria', {
            'fields': ('location', 'project_keyword', 'skills', 'match_all_skills')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_checked')
        }),
    )
    
    def match_count_display(self, obj):
        """Display current match count"""
        from accounts.views import _execute_saved_search_query
        matches = _execute_saved_search_query(obj)
        return matches.count()
    match_count_display.short_description = 'Current Matches'
    
    def new_match_count_display(self, obj):
        """Display new match count"""
        if not obj.is_active:
            return 0
        from accounts.views import _execute_saved_search_query
        matches = _execute_saved_search_query(obj)
        notified_candidate_ids = SearchMatchNotification.objects.filter(
            saved_search=obj
        ).values_list('candidate_id', flat=True)
        new_matches = matches.exclude(user_id__in=notified_candidate_ids)
        return new_matches.count()
    new_match_count_display.short_description = 'New Matches'


@admin.register(SearchMatchNotification)
class SearchMatchNotificationAdmin(admin.ModelAdmin):
    list_display = ['saved_search', 'candidate', 'notified_at']
    list_filter = ['notified_at', 'saved_search']
    search_fields = ['saved_search__name', 'candidate__username']
    readonly_fields = ['notified_at']
    
    fieldsets = (
        ('Notification', {
            'fields': ('saved_search', 'candidate', 'notified_at')
        }),
    )