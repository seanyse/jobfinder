from django.contrib import admin
from .models import Job

# Register your models here.
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'posted_by', 'location', 'remote_or_on_site', 'visa_sponsorship', 'salary', 'created_at']
    list_filter = ['remote_or_on_site', 'visa_sponsorship', 'location', 'created_at']
    search_fields = ['title', 'skills', 'location', 'posted_by__username']