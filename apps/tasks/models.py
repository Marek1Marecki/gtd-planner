# apps/tasks/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.tasks.domain.entities import TaskStatus


class RecurringPattern(models.Model):
    title = models.CharField(max_length=200)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey('projects.Project', null=True, blank=True, on_delete=models.SET_NULL)

    # Konfiguracja cyklu
    class RecurrenceType(models.TextChoices):
        FIXED = 'fixed', 'Sztywny (Kalendarzowy)'
        DYNAMIC = 'dynamic', 'Dynamiczny (Po wykonaniu)'

    recurrence_type = models.CharField(max_length=10, choices=RecurrenceType.choices, default=RecurrenceType.FIXED)

    # Interwał (np. co 7 dni)
    interval_days = models.PositiveIntegerField(default=7)

    # Dla dynamicznego: opóźnienie po wykonaniu
    # Dla sztywnego: data startu / następnego wywołania
    next_run_date = models.DateField(default=timezone.now)

    is_active = models.BooleanField(default=True)

    # Pola kopiowane do instancji zadania
    default_priority = models.IntegerField(default=3)
    default_duration_min = models.IntegerField(default=30)

    def __str__(self):
        return f"Pattern: {self.title} (Co {self.interval_days} dni)"


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

    is_critical_path = models.BooleanField(default=False)

    recurring_pattern = models.ForeignKey(
        RecurringPattern,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='generated_tasks'
    )

    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Kiedy przypomnieć o tym zadaniu?"
    )

    # Kontekst (Zazwyczaj jeden, np. "Gdzie jestem?")
    context = models.ForeignKey(
        'contexts.Context',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks'
    )

    # Tagi (Wiele, np. "Czego dotyczy?")
    tags = models.ManyToManyField(
        'contexts.Tag',
        blank=True,
        related_name='tasks'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title



from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from apps.projects.services.project_service import ProjectService

@receiver(m2m_changed, sender=Task.blocked_by.through)
def dependencies_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        if instance.project_id:
            service = ProjectService()
            service.recalculate_cpm(instance.project_id)

@receiver(post_save, sender=Task)
def task_changed(sender, instance, created, **kwargs):
    # Jeśli zmienił się czas trwania, też trzeba przeliczyć
    if instance.project_id:
        # Optymalizacja: sprawdź czy zmieniły się pola wpływające na CPM
        service = ProjectService()
        service.recalculate_cpm(instance.project_id)

@receiver(post_save, sender=Task)
def check_recurrence_on_completion(sender, instance, **kwargs):
    if instance.status == 'done' and instance.recurring_pattern:
        from apps.tasks.domain.services import RecurrenceService
        service = RecurrenceService()
        service.handle_task_completion(instance)
