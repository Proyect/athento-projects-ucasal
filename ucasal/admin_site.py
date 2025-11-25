"""
Personalización del sitio de administración de Django
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html


class UCASALAdminSite(AdminSite):
    site_header = "UCASAL - Sistema de Gestión"
    site_title = "UCASAL Admin"
    index_title = "Panel de Administración UCASAL"
    
    def index(self, request, extra_context=None):
        """
        Personalizar la página principal del admin
        """
        extra_context = extra_context or {}
        extra_context.update({
            'custom_message': 'Bienvenido al sistema de gestión de Actas y Títulos',
            'quick_links': [
                {'name': 'Actas', 'url': 'admin:actas_acta_changelist'},
                {'name': 'Títulos', 'url': 'admin:model_titulofile_changelist'},
                {'name': 'Archivos', 'url': 'admin:model_file_changelist'},
                {'name': 'Tipos de Documento', 'url': 'admin:model_doctype_changelist'},
                {'name': 'Estados', 'url': 'admin:model_lifecyclestate_changelist'},
                {'name': 'Series', 'url': 'admin:model_serie_changelist'},
                {'name': 'Teams', 'url': 'admin:model_team_changelist'},
            ]
        })
        return super().index(request, extra_context)

# Crear instancia personalizada del admin site
admin_site = UCASALAdminSite(name='ucasal_admin')






















