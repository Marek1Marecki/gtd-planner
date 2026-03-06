"""Django app configuration for goals."""

from django.apps import AppConfig


class GoalsConfig(AppConfig):
    """Django configuration for goals app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.goals"
    label = "goals"
