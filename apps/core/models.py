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
    wip_limit = models.PositiveIntegerField(default=5, help_text="Maksymalna liczba zadań w toku")

    # NOWE: Strategia algorytmu
    current_strategy = models.CharField(
        max_length=20,
        default='balanced',
        choices=[
            ('balanced', 'Zrównoważony'),
            ('warmup', 'Rozgrzewka (Proste/Krótkie)'),
            ('deep_work', 'Głęboka Praca (Projekt)'),
            ('deadline', 'Tryb Awaryjny (Terminy)')
        ]
    )

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


class GoogleCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_creds')
    token = models.TextField()  # Access Token
    refresh_token = models.TextField(null=True)  # Refresh Token (ważne!)
    token_uri = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    scopes = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Google Creds for {self.user.username}"

