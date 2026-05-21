from django.urls import re_path as url
# import endpoints as routes

app_name = 'ucasal'
# urlpatterns = [r.route for r in routes.__dict__.values() if 'module' in str(type(r)) and 'route' in r.__dict__]

#from endpoints import auth, docs, provider, dictionaries, invitation, upload, state, signup
from endpoints import( 
  actas,
  designaciones
)

urlpatterns = [
    *actas.routes,
    *designaciones.routes
]