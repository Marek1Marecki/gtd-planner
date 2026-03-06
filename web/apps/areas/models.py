"""Area models for GTD system."""

from django.conf import settings
from django.db import models


class Area(models.Model):
    """Represents an area of responsibility in GTD methodology."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # np. Praca, Dom, Zdrowie
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#6c757d")  # HEX, np. #0000FF
    icon = models.CharField(max_length=50, default="bi-folder", blank=True)  # Ikona Bootstrap

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return string representation of the area."""
        return self.name
