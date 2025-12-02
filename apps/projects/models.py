# apps/projects/models.py
from django.db import models
from django.conf import settings


class Project(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Hierarchia (Podprojekty)
    parent_project = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='subprojects'
    )

    # Powiązanie z Celem (Lazy reference string, aby uniknąć circular imports)
    goal = models.ForeignKey(
        'goals.Goal',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='projects'
    )

    status = models.CharField(
        max_length=20,
        default='active',
        choices=[('active', 'Active'), ('completed', 'Completed')]
    )
    deadline = models.DateField(null=True, blank=True)

    area = models.ForeignKey(
        'areas.Area',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='projects'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title