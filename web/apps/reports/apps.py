"""Django app configuration for reports."""

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Django configuration for reports app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"  # <-- WAŻNE: pełna ścieżka
    label = "reports"  # <-- WAŻNE: krótka nazwa
