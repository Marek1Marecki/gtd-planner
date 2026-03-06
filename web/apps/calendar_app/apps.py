"""Django app configuration for calendar app."""

from django.apps import AppConfig


class CalendarAppConfig(AppConfig):
    """Django configuration for calendar app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.calendar_app"
    label = "calendar_app"
