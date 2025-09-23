from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("recruiter", "Recruiter"),
        ("seeker", "Job Seeker"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

class Skill(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class Project(models.Model):
    title = models.CharField(max_length=120)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    def __str__(self): return self.title

class Profile(models.Model):
    user = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE, related_name="profile")
    headline = models.CharField(max_length=140)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)
    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    skills = models.ManyToManyField(Skill, blank=True)
    projects = models.ManyToManyField(Project, blank=True)

    def __str__(self): return f"{self.user.username} Profile"