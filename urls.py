from django.urls import re_path as url
# import ucasal2.endpoints as routes

app_name = 'ucasal2'
# urlpatterns = [r.route for r in routes.__dict__.values() if 'module' in str(type(r)) and 'route' in r.__dict__]

#from ucasal2.endpoints import auth, docs, provider, dictionaries, invitation, upload, state, signup
from ucasal2.endpoints import( 
  actas,
  designaciones
)

urlpatterns = [
    *actas.routes,
    *designaciones.routes
]