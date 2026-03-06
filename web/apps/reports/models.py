"""Report models for GTD system analytics."""

# apps/reports/models.py
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class ActivityLog(models.Model):
    """Logs user activities for tracking and analytics."""

    # Kto?
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Co zrobił? (Typ akcji)
    class ActionType(models.TextChoices):
        """Available action types for activity logging."""

        CREATED = "created", "Utworzono"
        UPDATED = "updated", "Zaktualizowano"
        STATUS_CHANGE = "status_change", "Zmiana Statusu"
        COMPLETED = "completed", "Ukończono"
        DELETED = "deleted", "Usunięto"

    action_type = models.CharField(max_length=20, choices=ActionType.choices)

    # Na czym? (Generic Relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Szczegóły (np. "Zmiana z TODO na DONE")
    description = models.TextField(blank=True)

    # Metadane (JSON - np. {"old_value": "todo", "new_value": "done"})
    details = models.JSONField(default=dict, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for ActivityLog model."""

        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        """Return string representation of the activity log."""
        return f"{self.user} - {self.action_type} - {self.timestamp}"


class ReviewSession(models.Model):
    """Represents a weekly review session for GTD methodology."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    # Treść
    reflection = models.TextField(blank=True, verbose_name="Refleksja (Co poszło dobrze/źle?)")
    next_week_priorities = models.TextField(blank=True, verbose_name="Priorytety na kolejny tydzień")

    class Meta:
        """Meta options for ReviewSession model."""

        ordering = ["-date"]  # Newest first

    def __str__(self) -> str:
        """Return string representation of the review session."""
        return f"Review {self.date.strftime('%Y-%m-%d')}"
