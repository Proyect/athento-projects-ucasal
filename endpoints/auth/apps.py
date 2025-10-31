from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'endpoints.auth'
    label = 'api_auth'  # Cambiar el label para evitar conflicto con django.contrib.auth

