from django.urls import re_path as url

from ucasal2.endpoints import titulos

app_name = 'ucasal2'

urlpatterns = [
    *titulos.routes,
]