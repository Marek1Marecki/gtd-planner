# apps/goals/models.py
from django.db import models
from django.conf import settings


class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    motivation = models.TextField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    progress = models.IntegerField(default=0, help_text="Postęp w procentach (0-100)")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title