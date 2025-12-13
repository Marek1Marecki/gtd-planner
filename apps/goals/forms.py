from django import forms
from .models import Goal

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'deadline', 'motivation', 'parent'] # Dodaj parent
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'motivation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtruj cele rodzicielskie tylko do usera (żeby nie widział cudzych)
        self.fields['parent'].queryset = Goal.objects.filter(user=user)