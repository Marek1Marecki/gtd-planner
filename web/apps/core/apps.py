"""Django app configuration for core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Django configuration for core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"  # Ważne: pełna ścieżka
    label = "core"  # Ważne: krótka nazwa
