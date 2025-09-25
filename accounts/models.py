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

class Education(models.Model):
    school = models.CharField(max_length=200)
    graduation_month = models.IntegerField(choices=[(i, i) for i in range(1, 13)])
    graduation_year = models.IntegerField()
    major = models.CharField(max_length=200)
    degree = models.CharField(max_length=100)
    
    def __str__(self): return f"{self.degree} in {self.major} from {self.school}"

class WorkExperience(models.Model):
    company = models.CharField(max_length=200)
    description = models.TextField()
    
    def __str__(self): return f"{self.company}"

class Profile(models.Model):
    user = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE, related_name="profile")
    headline = models.CharField(max_length=140)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)
    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)

    skills = models.ManyToManyField(Skill, blank=True)
    projects = models.ManyToManyField(Project, blank=True)
    education = models.ManyToManyField(Education, blank=True)
    work_experience = models.ManyToManyField(WorkExperience, blank=True)

    def __str__(self): return f"{self.user.username} Profile"