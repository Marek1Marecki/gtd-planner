#apps/tasks/forms.py
from django import forms
from .models import RecurringPattern

class RecurrenceForm(forms.ModelForm):
    # Checkboxy dla dni tygodnia
    DAYS = [
        ('MO', 'Poniedziałek'), ('TU', 'Wtorek'), ('WE', 'Środa'),
        ('TH', 'Czwartek'), ('FR', 'Piątek'), ('SA', 'Sobota'), ('SU', 'Niedziela')
    ]
    week_days = forms.MultipleChoiceField(
        choices=DAYS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Wybierz dni"
    )

    class Meta:
        model = RecurringPattern
        fields = ['title', 'frequency', 'interval', 'end_date', 'max_occurrences', 'is_dynamic']
        widgets = {
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'interval': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'max_occurrences': forms.NumberInput(attrs={'class': 'form-control'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
        }