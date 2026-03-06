# apps/goals/models.py
from django.conf import settings
from django.db import models


class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="subgoals")
    title = models.CharField(max_length=200)
    motivation = models.TextField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    progress = models.IntegerField(default=0, help_text="Postęp w procentach (0-100)")
    area = models.ForeignKey("areas.Area", null=True, blank=True, on_delete=models.SET_NULL, related_name="goals")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title
