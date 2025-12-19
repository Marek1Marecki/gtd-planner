# apps/tasks/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.tasks.domain.entities import TaskStatus
from dateutil.rrule import rrulestr


class RecurringPattern(models.Model):
    title = models.CharField(max_length=200)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey('projects.Project', null=True, blank=True, on_delete=models.SET_NULL)

    # Typ interwału
    class RecurrenceFrequency(models.TextChoices):
        DAILY = 'DAILY', 'Codziennie'
        WEEKLY = 'WEEKLY', 'Co tydzień'
        MONTHLY = 'MONTHLY', 'Co miesiąc'
        YEARLY = 'YEARLY', 'Co rok'

    frequency = models.CharField(
        max_length=20,
        choices=RecurrenceFrequency.choices,
        default=RecurrenceFrequency.WEEKLY
    )

    interval = models.PositiveIntegerField(default=1, help_text="Co ile? (np. co 2 tygodnie)")

    # Wybór dni tygodnia (dla WEEKLY) - przechowamy jako JSON lub oddzielne boole
    # Najprościej: JSON list np. ['MO', 'WE']
    week_days = models.JSONField(default=list, blank=True)

    # Warunki końca
    end_date = models.DateField(null=True, blank=True)
    max_occurrences = models.PositiveIntegerField(null=True, blank=True, help_text="Zakończ po X wystąpieniach")

    # Tryb generowania (to zostaje z naszej starej logiki)
    # Fixed = generuj wg kalendarza (RRULE)
    # Dynamic = generuj po wykonaniu (tu RRULE jest mniej przydatne, ale interwał się przyda)
    is_dynamic = models.BooleanField(default=False, help_text="Czy generować po wykonaniu poprzedniego?")

    # Dla dynamicznego: opóźnienie po wykonaniu
    # Dla sztywnego: data startu / następnego wywołania
    next_run_date = models.DateField(default=timezone.now)

    is_active = models.BooleanField(default=True)

    # Pola kopiowane do instancji zadania
    default_priority = models.IntegerField(default=3)
    default_duration_min = models.IntegerField(default=30)

    # Liczniki skuteczności
    generated_count = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Pattern: {self.title} ({self.get_frequency_display()})"

    @property
    def completion_rate(self):
        if self.generated_count == 0: return 0
        return int((self.completed_count / self.generated_count) * 100)

    def get_rrule_string(self):
        """Generuje string zgodny z RFC 5545 na podstawie pól modelu."""
        from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU

        # Mapowanie stringów na obiekty dateutil
        day_map = {
            'MO': MO, 'TU': TU, 'WE': WE, 'TH': TH, 'FR': FR, 'SA': SA, 'SU': SU
        }

        parts = [f"FREQ={self.frequency}"]
        parts.append(f"INTERVAL={self.interval}")

        if self.frequency == 'WEEKLY' and self.week_days:
            # week_days to np. ['MO', 'TH']
            days_str = ",".join(self.week_days)
            parts.append(f"BYDAY={days_str}")

        if self.max_occurrences:
            # Musimy odjąć to co już wygenerowano?
            # RRULE COUNT dotyczy całkowitej liczby w serii.
            # Jeśli edytujemy pattern, to COUNT liczy się od startu reguły (dtstart).
            parts.append(f"COUNT={self.max_occurrences}")

        if self.end_date:
            parts.append(f"UNTIL={self.end_date.strftime('%Y%m%dT%H%M%S')}")

        return ";".join(parts)


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
    is_milestone = models.BooleanField(default=False, help_text="Oznacza punkt kontrolny projektu")

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

    area = models.ForeignKey(
        'areas.Area',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks'
    )

    goal = models.ForeignKey('goals.Goal', null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')

    # NOWE POLE: Data wejścia w stan gotowości
    ready_since = models.DateTimeField(null=True, blank=True, help_text="Kiedy zadanie stało się wykonalne (TODO/SCHEDULED)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Automatyczne dziedziczenie obszaru z projektu
        if self.project and self.project.area and not self.area:
            self.area = self.project.area
        super().save(*args, **kwargs)


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
        # Import z nowego miejsca (przez __init__)
        from apps.tasks.domain.services import RecurrenceService
        service = RecurrenceService()
        service.handle_task_completion(instance)


class ChecklistItem(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='checklist_items', null=True, blank=True)
    recurring_pattern = models.ForeignKey(RecurringPattern, on_delete=models.CASCADE, related_name='template_items', null=True, blank=True)

    text = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text


    @property
    def checklist_progress(self):
        total = self.checklist_items.count()
        if total == 0: return 0
        done = self.checklist_items.filter(is_completed=True).count()
        return int((done / total) * 100)
