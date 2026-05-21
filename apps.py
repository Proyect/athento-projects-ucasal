#from core.apps import IntegrationAppConfig
from django.apps import AppConfig
from django.urls import re_path as url, include


class UcasalAppConfig(AppConfig):
    name = 'ucasal'

    def ready(self):
        pass

    def get_urlpatterns(self):
        return [url(r'^ucasal/api/', include('ucasal.urls', namespace='ucasal'))]
