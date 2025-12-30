# apps/notes/models.py
from django.db import models
from django.conf import settings


class Note(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, help_text="Markdown supported")

    # Powiązania (Opcjonalne)
    project = models.ForeignKey(
        'projects.Project',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='notes'
    )
    task = models.ForeignKey(
        'tasks.Task',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='notes'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title