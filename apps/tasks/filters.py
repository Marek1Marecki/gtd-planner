import django_filters
from django import forms
from .models import Task
from apps.contexts.models import Context

class TaskFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        label="Tytuł zawiera",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Szukaj...'})
    )
    status = django_filters.ChoiceFilter(
        choices=Task.StatusChoices.choices,
        label="Status",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    context = django_filters.ModelChoiceFilter(
        queryset=Context.objects.all(),
        label="Kontekst",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    duration_max = django_filters.NumberFilter(
        field_name='duration_min', # Filtrujemy po duration_min <= wartość
        lookup_expr='lte',
        label="Maks czas (min)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    energy_required = django_filters.ChoiceFilter(
        choices=[(1, 'Niska'), (2, 'Średnia'), (3, 'Wysoka')],
        label="Energia",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Task
        fields = ['project', 'is_private']