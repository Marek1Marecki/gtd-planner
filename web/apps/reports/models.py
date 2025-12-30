# apps/reports/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ActivityLog(models.Model):
    # Kto?
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Co zrobił? (Typ akcji)
    class ActionType(models.TextChoices):
        CREATED = 'created', 'Utworzono'
        UPDATED = 'updated', 'Zaktualizowano'
        STATUS_CHANGE = 'status_change', 'Zmiana Statusu'
        COMPLETED = 'completed', 'Ukończono'
        DELETED = 'deleted', 'Usunięto'

    action_type = models.CharField(max_length=20, choices=ActionType.choices)

    # Na czym? (Generic Relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Szczegóły (np. "Zmiana z TODO na DONE")
    description = models.TextField(blank=True)

    # Metadane (JSON - np. {"old_value": "todo", "new_value": "done"})
    details = models.JSONField(default=dict, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.timestamp}"


class ReviewSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    # Treść
    reflection = models.TextField(blank=True, verbose_name="Refleksja (Co poszło dobrze/źle?)")
    next_week_priorities = models.TextField(blank=True, verbose_name="Priorytety na kolejny tydzień")

    def __str__(self):
        return f"Review {self.date.strftime('%Y-%m-%d')}"
