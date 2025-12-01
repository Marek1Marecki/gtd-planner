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
