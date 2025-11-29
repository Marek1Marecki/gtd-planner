# apps/tasks/models.py
from django.db import models
from django.conf import settings
from apps.tasks.domain.entities import TaskStatus


class Task(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Używamy TextChoices dla wygody w Adminie, ale mapujemy to na Enum domenowy
    class StatusChoices(models.TextChoices):
        INBOX = 'inbox', 'Inbox'
        TODO = 'todo', 'To Do'
        SCHEDULED = 'scheduled', 'Scheduled'
        DONE = 'done', 'Done'
        WAITING = 'waiting', 'Waiting'
        BLOCKED = 'blocked', 'Blocked'
        DELEGATED = 'delegated', 'Delegated'
        POSTPONED = 'postponed', 'Postponed'
        PAUSED = 'paused', 'Paused'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.INBOX
    )

    # Czas
    duration_min = models.PositiveIntegerField(null=True, blank=True)
    duration_max = models.PositiveIntegerField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    is_fixed_time = models.BooleanField(default=False)

    # Priorytety
    priority = models.IntegerField(default=3)
    energy_required = models.IntegerField(default=2)
    complexity = models.IntegerField(default=1)

    # Kontekst
    is_private = models.BooleanField(default=False)
    percent_complete = models.PositiveIntegerField(default=0)

    # Powiazanie z Projektami
    project = models.ForeignKey(
        'projects.Project',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks'
    )

    # Nowe pole: Zależności
    # "blocked_by" oznacza "ja zależe od tych zadań"
    # "blocking" (related_name) oznacza "ja blokuję te zadania"
    blocked_by = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='blocking',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title