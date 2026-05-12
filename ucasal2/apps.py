#from core.apps import IntegrationAppConfig
from django.apps import AppConfig
from django.urls import re_path as url, include


class Ucasal2AppConfig(AppConfig):
    name = 'ucasal2'

    def ready(self):
        pass

    def get_urlpatterns(self):
        return [url(r'^ucasal2/api/', include('ucasal2.urls', namespace='ucasal2'))]
