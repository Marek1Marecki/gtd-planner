from django.urls import path
from . import views

urlpatterns = [
    path('', views.daily_view, name='calendar_daily'),
    path('week/', views.weekly_view, name='calendar_weekly'),
    path('month/', views.monthly_view, name='calendar_monthly'),

]