"""Django app configuration for notes."""

from django.apps import AppConfig


class NotesConfig(AppConfig):
    """Django configuration for notes app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notes"
    label = "notes"
