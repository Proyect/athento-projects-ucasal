# endpoints/actas/views.py
from django.http import HttpResponse

def example_view(request):
    return HttpResponse("This is an example view.")