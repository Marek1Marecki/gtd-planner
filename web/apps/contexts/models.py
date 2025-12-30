# apps/contexts/models.py
from django.db import models
from django.conf import settings


class Context(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # np. @biuro, @dom
    icon = models.CharField(max_length=50, blank=True, default="bi-tag")  # np. bi-house
    color = models.CharField(max_length=7, default="#6c757d")  # HEX, np. #ff0000

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # np. #pilne, #telefon
    color = models.CharField(max_length=7, default="#17a2b8")

    def __str__(self):
        return self.name