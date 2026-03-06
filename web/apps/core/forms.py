from django import forms

from .models import UserProfile


class UserProfileForm(forms.ModelForm):  # type: ignore
    class Meta:
        model = UserProfile
        fields = [
            "work_start_hour",
            "work_end_hour",
            "personal_start_hour",
            "personal_end_hour",
            "morning_buffer_minutes",
            "evening_buffer_minutes",
            "wip_limit",
            "current_strategy",
        ]
        widgets = {
            "work_start_hour": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "work_end_hour": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "personal_start_hour": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "personal_end_hour": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "morning_buffer_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "evening_buffer_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "wip_limit": forms.NumberInput(attrs={"class": "form-control"}),
            "current_strategy": forms.Select(attrs={"class": "form-control"}),
        }
