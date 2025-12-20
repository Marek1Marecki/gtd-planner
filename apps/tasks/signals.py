# apps/tasks/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from apps.reports.services import ActivityLogger
from apps.reports.models import ActivityLog
from django.utils import timezone
from .models import Task
from .domain.entities import TaskStatus

@receiver(pre_save, sender=Task)
def track_task_changes(sender, instance, **kwargs):
    """
    Przed zapisem sprawdzamy stary stan zadania, żeby wykryć zmiany.
    Zapisujemy to w tymczasowym atrybucie instancji.
    """
    if instance.id:
        try:
            old_instance = Task.objects.get(id=instance.id)
            instance._old_status = old_instance.status
        except Task.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Task)
def log_task_changes(sender, instance, created, **kwargs):
    """
    Po zapisie sprawdzamy, co się zmieniło i logujemy.
    """
    user = instance.user  # Zakładamy, że user jest w modelu Task

    if created:
        ActivityLogger.log(
            user, instance,
            ActivityLog.ActionType.CREATED,
            f"Utworzono zadanie: {instance.title}"
        )

    elif hasattr(instance, '_old_status') and instance._old_status != instance.status:
        # Wykryto zmianę statusu!
        description = f"Zmiana statusu: {instance.get_status_display()}"

        # Specjalny przypadek: Ukończenie
        action_type = ActivityLog.ActionType.STATUS_CHANGE
        if instance.status == 'done':
            action_type = ActivityLog.ActionType.COMPLETED
            description = "Zadanie ukończone! 🎉"

        ActivityLogger.log(
            user, instance,
            action_type,
            description,
            details={
                'old_status': instance._old_status,
                'new_status': instance.status
            }
        )


@receiver(post_save, sender=Task)
def update_goal_progress(sender, instance, **kwargs):
    """Przelicz postęp projektu i celu po zmianie zadania."""
    if instance.project:
        # 1. Przelicz Projekt (opcjonalnie, jeśli projekt ma pole progress)
        # ...

        # 2. Przelicz Cel (jeśli projekt ma cel)
        goal = instance.project.goal
        if goal:
            from django.db.models import Count, Q

            # Pobierz wszystkie zadania powiązane z tym celem (przez projekty)
            # To wymaga odwrotnego lookupu.
            # Załóżmy strukturę: Goal -> (projects) -> Project -> (tasks) -> Task

            # Agregacja:
            # Policz wszystkie zadania w projektach tego celu
            stats = Task.objects.filter(project__goal=goal).aggregate(
                total=Count('id'),
                done=Count('id', filter=Q(status='done'))
            )

            total = stats['total']
            done = stats['done']

            new_progress = int((done / total) * 100) if total > 0 else 0

            if goal.progress != new_progress:
                goal.progress = new_progress
                goal.save()


@receiver(pre_save, sender=Task)
def update_ready_since(sender, instance, **kwargs):
    """Aktualizuje ready_since przy wejściu w status aktywny."""

    active_statuses = ['todo', 'scheduled']
    inactive_statuses = ['blocked', 'waiting', 'delegated', 'postponed', 'paused', 'inbox']

    if instance.id:
        try:
            old_instance = Task.objects.get(id=instance.id)
            old_status = old_instance.status
        except Task.DoesNotExist:
            old_status = None

        # Scenariusz 1: Nowe zadanie tworzone od razu jako TODO
        if not old_status and instance.status in active_statuses:
            instance.ready_since = timezone.now()

        # Scenariusz 2: Zmiana z NIEAKTYWNEGO na AKTYWNY (np. Blocked -> Todo)
        elif old_status in inactive_statuses and instance.status in active_statuses:
            instance.ready_since = timezone.now()

        # Scenariusz 3: Zadanie wciąż nieaktywne -> czyścimy ready_since (opcjonalne, ale czystsze)
        elif instance.status in inactive_statuses:
            instance.ready_since = None

    else:
        # Nowe zadanie
        if instance.status in active_statuses:
            instance.ready_since = timezone.now()


@receiver(post_save, sender=Task)
def track_recurring_completion(sender, instance, created, **kwargs):
    """Zlicza ukończenie zadania cyklicznego."""
    # Jeśli zadanie jest DONE, ma szablon i właśnie zmieniliśmy status
    if not created and instance.status == 'done' and instance.recurring_pattern:
        if hasattr(instance, '_old_status') and instance._old_status != 'done':
            # Inkrementacja licznika
            # Używamy F() dla bezpieczeństwa przy współbieżności (opcjonalnie)
            from django.db.models import F
            instance.recurring_pattern.completed_count = F('completed_count') + 1
            instance.recurring_pattern.save()


@receiver(pre_save, sender=Task)
def set_completed_at(sender, instance, **kwargs):
    # Jeśli status zmienia się na DONE, a data jest pusta -> ustaw teraz
    if instance.status == 'done' and not instance.completed_at:
        instance.completed_at = timezone.now()
    # Jeśli status zmienia się z DONE na coś innego (reopen) -> wyczyść
    elif instance.status != 'done' and instance.completed_at:
        instance.completed_at = None
