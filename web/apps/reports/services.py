"""Activity logging services for reports."""

# apps/reports/services.py
from typing import Any

from django.contrib.contenttypes.models import ContentType

from .models import ActivityLog


class ActivityLogger:
    """Service for logging user activities and events."""

    @staticmethod
    def log(user: Any, obj: Any, action_type: str, description: str = "", details: Any = None) -> None:
        """Uniwersalna metoda do logowania zdarzeń."""
        if not user or not user.is_authenticated:
            return None  # Nie logujemy działań systemu/anonimowych (chyba że chcemy)

        ActivityLog.objects.create(
            user=user,
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.id,
            action_type=action_type,
            description=description,
            details=details or {},
        )
