# apps/tasks/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Task
from apps.reports.services import ActivityLogger
from apps.reports.models import ActivityLog


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