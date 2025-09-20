# jobs/models.py
from django.db import models
from django.conf import settings

class Job(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    skills = models.TextField(help_text="List required skills, separated by commas")
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Annual salary in USD")
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    location = models.CharField(max_length=200, null=True, blank=True)
    
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
