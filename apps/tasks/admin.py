from django.contrib import admin
from .models import Task, RecurringPattern  # Importujemy też nowy model

admin.site.register(Task)

# Rejestracja RecurringPattern z ładną listą
@admin.register(RecurringPattern)
class RecurringPatternAdmin(admin.ModelAdmin):
    list_display = ('title', 'recurrence_type', 'interval_days', 'next_run_date', 'is_active')
    list_filter = ('recurrence_type', 'is_active')
    search_fields = ('title',)