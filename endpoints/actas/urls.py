# endpoints/actas/urls.py
from django.urls import path, re_path
from . import views
from .actas import routes

urlpatterns = [
    # Rutas básicas de actas
    path('example/', views.example_view, name='example_view'),
] + routes