"""
URLs para endpoints de autenticación
"""
from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    path('login/', views.login, name='login'),
    path('refresh/', views.refresh_token, name='refresh'),
]

