from django.urls import path
from . import views

urlpatterns = [
    path('', views.note_list_view, name='note_list'),
    path('new/', views.note_create_view, name='note_create'),
    path('<int:pk>/', views.note_detail_view, name='note_detail'),
]