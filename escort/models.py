from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class EscortSession(models.Model):
    STATUS_CHOICES = [
        ("Requested", "Requested"),
        ("Pending", "Pending"),
        ("Active", "Active"),
        ("Completed", "Completed"),
        ("Panic", "Panic"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    location = models.CharField(max_length=100, blank=True, null=True)
    destination = models.CharField(max_length=200, blank=True, null=True)
    eta = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.status} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
