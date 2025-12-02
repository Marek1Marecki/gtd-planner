from django.contrib import admin
from .models import Habit, HabitLog

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('title', 'current_streak', 'longest_streak', 'last_completed_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title',)

@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('habit', 'date')
    list_filter = ('date', 'habit')