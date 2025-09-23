from django.contrib import admin
from .models import Job, Application

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'posted_by', 'location', 'remote_or_on_site', 'visa_sponsorship', 'salary', 'created_at']
    list_filter = ['remote_or_on_site', 'visa_sponsorship', 'location', 'created_at']
    search_fields = ['title', 'skills', 'location', 'posted_by__username']

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'job', 'status', 'applied_at', 'updated_at']
    list_filter = ['status', 'applied_at', 'job__posted_by']
    search_fields = ['applicant__username', 'job__title']
    readonly_fields = ['applied_at']