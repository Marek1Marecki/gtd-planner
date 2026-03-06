"""Django app configuration for habits."""

from django.apps import AppConfig


class HabitsConfig(AppConfig):
    """Django configuration for habits app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.habits"
    label = "habits"
