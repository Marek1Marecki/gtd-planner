from django.contrib import admin

from .models import ChecklistItem, RecurringPattern, Task

admin.site.register(Task)


class ChecklistItemInline(admin.TabularInline):  # type: ignore
    model = ChecklistItem
    extra = 1
    fields = ("text", "order")  # Nie pokazujemy is_completed w szablonie


# Rejestracja RecurringPattern z ładną listą
@admin.register(RecurringPattern)
class RecurringPatternAdmin(admin.ModelAdmin):  # type: ignore
    # Zaktualizuj nazwy pól
    list_display = ("title", "frequency", "interval", "next_run_date", "is_active", "generated_count")
    list_filter = ("frequency", "is_active", "is_dynamic")
    search_fields = ("title",)
    inlines = [ChecklistItemInline]
