from django.contrib import admin
from .models import Job, Application
import csv
from django.http import HttpResponse

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "city", "state", "remote_or_on_site", "visa_sponsorship", "salary", "posted_by", "created_at")
    search_fields = ("title", "company", "city", "state", "posted_by__username")
    list_filter = ("remote_or_on_site", "visa_sponsorship", "state", "created_at")
    actions = ["export_jobs_as_csv"]

    def export_jobs_as_csv(self, request, queryset):
        """
        Admin action to export selected Job records as CSV for reporting.
        """
        # If no objects selected, export all
        if not queryset.exists():
            queryset = self.model.objects.all()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="jobs_report.csv"'
        writer = csv.writer(response)

        # CSV Header
        writer.writerow([
            "ID",
            "Title",
            "Company",
            "Skills",
            "Salary (USD)",
            "Remote/On-site",
            "Visa Sponsorship",
            "Location",
            "City",
            "State",
            "Latitude",
            "Longitude",
            "Posted By",
            "Created At",
            "Updated At",
        ])

        # CSV Rows
        for job in queryset:
            writer.writerow([
                job.id,
                job.title,
                job.company,
                job.skills,
                job.salary if job.salary else "",
                job.get_remote_or_on_site_display(),
                job.get_visa_sponsorship_display(),
                job.location,
                job.city,
                job.state,
                job.latitude,
                job.longitude,
                job.posted_by.username if job.posted_by else "N/A",
                job.created_at.strftime("%Y-%m-%d"),
                job.updated_at.strftime("%Y-%m-%d"),
            ])

        return response

    export_jobs_as_csv.short_description = "Export selected Jobs as CSV"

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "applied_at", "updated_at")
    search_fields = ("applicant__username", "job__title")
    list_filter = ("status", "applied_at")
    actions = ["export_applications_as_csv"]

    def export_applications_as_csv(self, request, queryset):
        """
        Admin action to export selected Application records as CSV.
        """
        # If no objects selected, export all
        if not queryset.exists():
            queryset = self.model.objects.all()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="applications_report.csv"'
        writer = csv.writer(response)

        # CSV Header
        writer.writerow([
            "Job Title",
            "Applicant Username",
            "Applicant Email",
            "Status",
            "Cover Letter",
            "Applied At",
            "Updated At",
        ])

        # CSV Rows
        for app in queryset.select_related("job", "applicant"):
            writer.writerow([
                app.job.title,
                app.applicant.username,
                getattr(app.applicant, "email", ""),
                app.get_status_display(),
                app.cover_letter,
                app.applied_at.strftime("%Y-%m-%d"),
                app.updated_at.strftime("%Y-%m-%d"),
            ])

        return response

    export_applications_as_csv.short_description = "Export selected Applications as CSV"

