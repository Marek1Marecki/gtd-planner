"""Django app configuration for notifications."""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Django configuration for notifications app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
