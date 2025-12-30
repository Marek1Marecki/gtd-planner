from django.contrib import admin
from .models import Area

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'user')
    search_fields = ('name',)