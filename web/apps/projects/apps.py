"""Django app configuration for projects."""

from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Django configuration for projects app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    label = "projects"
