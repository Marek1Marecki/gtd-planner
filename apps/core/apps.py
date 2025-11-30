from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'  # Ważne: pełna ścieżka
    label = 'core'      # Ważne: krótka nazwa