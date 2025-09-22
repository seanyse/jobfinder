from django.contrib import admin

# Register your models here.
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "city", "state", "posted_at")
    search_fields = ("title", "company", "city", "state")
