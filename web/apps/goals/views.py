from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import Goal
from .forms import GoalForm


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


@login_required
def goal_create_view(request):
    if request.method == 'POST':
        form = GoalForm(request.user, request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('goal_list')
    else:
        form = GoalForm(request.user)

    return render(request, 'goals/goal_form.html', {'form': form, 'title': 'Nowy Cel'})


@login_required
def goal_edit_view(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = GoalForm(request.user, request.POST, instance=goal)
        if form.is_valid():
            form.save()
            return redirect('goal_list')
    else:
        form = GoalForm(request.user, instance=goal)

    return render(request, 'goals/goal_form.html', {'form': form, 'title': f'Edytuj: {goal.title}'})
