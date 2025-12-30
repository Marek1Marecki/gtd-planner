from django.apps import AppConfig

class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tasks'  # Ważne: pełna ścieżka z 'apps.'
    label = 'tasks'      # Ważne: krótka nazwa, żeby Django widziało to jako 'tasks'

    def ready(self):
        import apps.tasks.signals