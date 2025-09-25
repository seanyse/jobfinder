# jobs/models.py
from django.db import models
from django.conf import settings

class Job(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    skills = models.TextField(help_text="List required skills, separated by commas")
    company = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    skills = models.TextField(help_text="List required skills, separated by commas")
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Annual salary in USD")
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    location = models.CharField(max_length=200, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    city = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=120, blank=True, default="")

    REMOTE_CHOICES = (
        ('remote', 'Remote'),
        ('on_site', 'On-site'),
        ('hybrid', 'Hybrid'),
    )
    remote_or_on_site = models.CharField(max_length=10, choices=REMOTE_CHOICES, default='on_site')
    
    VISA_CHOICES = (
        ('yes', 'Visa Sponsorship Available'),
        ('no', 'No Visa Sponsorship'),
    )
    visa_sponsorship = models.CharField(max_length=3, choices=VISA_CHOICES, default='no')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Application(models.Model):
    STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('review', 'Under Review'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('closed', 'Closed'),
    )
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    cover_letter = models.TextField(blank=True, help_text="Optional cover letter")
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('job', 'applicant')  # Prevent duplicate applications
    
    def __str__(self):
        return f"{self.applicant.username} -> {self.job.title} ({self.status})"
