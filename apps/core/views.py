from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserProfileForm


@login_required
def settings_view(request):
    try:
        profile = request.user.profile
    except:
        # Fallback jeśli profil nie istnieje (np. stary user)
        from .models import UserProfile
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()

            # Zapisz profil energetyczny z tabeli HTML
            energy_data = {}
            for hour in range(0, 24):
                key = f"energy_{hour:02d}"  # np. energy_09
                val = request.POST.get(key)
                if val:
                    energy_data[f"{hour:02d}"] = int(val)

            profile.energy_profile = energy_data
            profile.save()

            messages.success(request, "Ustawienia zapisane pomyślnie!")
            return redirect('settings')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'core/settings.html', {
        'form': form,
        'energy_range': range(0, 24),
        'current_energy': profile.energy_profile
    })