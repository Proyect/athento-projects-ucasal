from django.urls import path, include
from django.contrib import admin
# import ucasal.endpoints as routes

app_name = 'ucasal'
# urlpatterns = [r.route for r in routes.__dict__.values() if 'module' in str(type(r)) and 'route' in r.__dict__]


urlpatterns = [
    path('admin/', admin.site.urls),
    path('actas/', include('endpoints.actas.urls')),
]