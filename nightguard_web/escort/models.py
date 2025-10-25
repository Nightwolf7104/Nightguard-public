from django.db import models
from django.contrib.auth.models import User

class EscortSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default="Pending")
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.status} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
