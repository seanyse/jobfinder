from django.db import models

class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    # Location fields (you can also add address if you want)
    latitude = models.FloatField()
    longitude = models.FloatField()
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    posted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} @ {self.company or 'Unknown'}"
