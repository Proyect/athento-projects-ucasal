from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('files/', views.create_file_view, name='create_file'),
    path('files/<uuid:uuid>/', views.update_file_view, name='update_file'),
    path('files/<uuid:uuid>/delete/', views.delete_file_view, name='delete_file'),
    path('files/<uuid:uuid>/detail/', views.get_file_view, name='get_file'),
    path('files/<uuid:uuid>/download', views.download_file_view, name='download_file'),
    path('search/query/', views.search_query_view, name='search_query'),
    path('search/resultset/', views.search_resultset_view, name='search_resultset'),
]
