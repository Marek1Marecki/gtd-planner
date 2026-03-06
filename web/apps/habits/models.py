"""Habit tracking models for GTD system."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Habit(models.Model):
    """Represents a habit that can be tracked daily."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    # Statystyki
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)

    # Ostatnie wykonanie
    last_completed_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    area = models.ForeignKey("areas.Area", null=True, blank=True, on_delete=models.SET_NULL, related_name="habits")

    def __str__(self) -> str:
        """Return string representation of the habit."""
        return self.title


class HabitLog(models.Model):
    """Represents a log entry for habit completion."""

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField(default=timezone.now)

    class Meta:
        """Meta options for HabitLog model."""

        unique_together = ("habit", "date")  # Jeden wpis na dzień
        ordering = ["-date"]  # Najnowsze na górze

    def __str__(self) -> str:
        """Return string representation of the habit log."""
        return f"{self.habit.title} - {self.date}"
