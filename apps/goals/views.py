from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import Goal


@login_required
def goal_list_view(request):
    """Dashboard strategiczny: Lista celów z postępem."""
    goals = Goal.objects.filter(user=request.user).annotate(
        # Obliczanie postępu na poziomie bazy danych (optymalizacja)
        # Zakładamy, że postęp jest zapisywany w modelu Goal przez sygnały/serwis,
        # ale dla pewności możemy go też doliczać tu, jeśli model tego nie ma.
        # W naszym modelu Goal mamy pole 'progress' (float 0-1), które powinno być aktualizowane.
        # Jeśli nie mamy automatyzacji aktualizacji pola progress, wyświetlimy to co jest.
    ).order_by('deadline')

    return render(request, 'goals/goal_list.html', {'goals': goals})