# apps/core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Ramy czasowe (domyślnie 9-17 praca, 17-22 prywatne)
    work_start_hour = models.TimeField(default="09:00")
    work_end_hour = models.TimeField(default="17:00")
    personal_start_hour = models.TimeField(default="17:00")
    personal_end_hour = models.TimeField(default="22:00")

    # Bufory (w minutach)
    morning_buffer_minutes = models.PositiveIntegerField(default=30)
    between_tasks_buffer_minutes = models.PositiveIntegerField(default=5)
    evening_buffer_minutes = models.PositiveIntegerField(default=30)

    # Profil Energetyczny (JSON: {godzina: poziom})
    # Poziom: 1 (Low), 2 (Mid), 3 (High)
    energy_profile = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


# Sygnał: Twórz profil automatycznie przy tworzeniu Usera
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()