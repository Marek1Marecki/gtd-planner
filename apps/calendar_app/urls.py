from django.urls import path
from . import views

urlpatterns = [
    path('', views.daily_view, name='calendar_daily'),
]