"""
Admin personalizado para modelos del sistema
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .File import File, Doctype, LifeCycleState, Team, Serie
import json


@admin.register(Doctype)
class DoctypeAdmin(admin.ModelAdmin):
    """Admin para tipos de documentos"""
    list_display = ['name', 'label', 'uuid_short', 'files_count']
    search_fields = ['name', 'label', 'uuid']
    readonly_fields = ['uuid']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'name', 'label')
        }),
    )
    
    def uuid_short(self, obj):
        return str(obj.uuid)[:8] + '...'
    uuid_short.short_description = 'UUID'
    
    def files_count(self, obj):
        count = obj.files.count()
        if count > 0:
            url = reverse('admin:model_file_changelist') + f'?doctype_obj__id__exact={obj.uuid}'
            return format_html('<a href="{}">{} archivos</a>', url, count)
        return '0 archivos'
    files_count.short_description = 'Archivos'


@admin.register(LifeCycleState)
class LifeCycleStateAdmin(admin.ModelAdmin):
    """Admin para estados del ciclo de vida"""
    list_display = ['name', 'maximum_time', 'uuid_short', 'files_count']
    search_fields = ['name']
    list_filter = ['maximum_time']
    readonly_fields = ['uuid']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'name')
        }),
        ('Configuración', {
            'fields': ('maximum_time',)
        }),
    )
    
    def uuid_short(self, obj):
        return str(obj.uuid)[:8] + '...'
    uuid_short.short_description = 'UUID'
    
    def files_count(self, obj):
        count = obj.files.count()
        if count > 0:
            url = reverse('admin:model_file_changelist') + f'?life_cycle_state_obj__id__exact={obj.uuid}'
            return format_html('<a href="{}">{} archivos</a>', url, count)
        return '0 archivos'
    files_count.short_description = 'Archivos'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin para Teams"""
    list_display = ['name', 'label', 'uuid_short', 'series_count']
    search_fields = ['name', 'label']
    readonly_fields = ['uuid']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'name', 'label')
        }),
    )
    
    def uuid_short(self, obj):
        return str(obj.uuid)[:8] + '...'
    uuid_short.short_description = 'UUID'
    
    def series_count(self, obj):
        count = obj.serie_set.count()
        return f'{count} series'
    series_count.short_description = 'Series'


@admin.register(Serie)
class SerieAdmin(admin.ModelAdmin):
    """Admin para Series (Espacios)"""
    list_display = ['name', 'label', 'team', 'uuid_short', 'files_count']
    list_filter = ['team']
    search_fields = ['name', 'label', 'team__name']
    readonly_fields = ['uuid']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'name', 'label')
        }),
        ('Relaciones', {
            'fields': ('team',)
        }),
    )
    
    def uuid_short(self, obj):
        return str(obj.uuid)[:8] + '...'
    uuid_short.short_description = 'UUID'
    
    def files_count(self, obj):
        count = obj.files.count()
        if count > 0:
            url = reverse('admin:model_file_changelist') + f'?serie__id__exact={obj.uuid}'
            return format_html('<a href="{}">{} archivos</a>', url, count)
        return '0 archivos'
    files_count.short_description = 'Archivos'


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """Admin para archivos del sistema"""
    list_display = [
        'titulo_display',
        'doctype_display',
        'lifecycle_state_display',
        'serie',
        'filename',
        'created_at',
        'removed_badge'
    ]
    
    list_filter = [
        'doctype_obj',
        'life_cycle_state_obj',
        'serie',
        'removed',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'uuid',
        'titulo',
        'filename',
        'doctype_legacy',
        'life_cycle_state_legacy'
    ]
    
    readonly_fields = [
        'uuid',
        'created_at',
        'updated_at',
        'life_cycle_state_date',
        'metadata_display',
        'features_display'
    ]
    
    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'titulo', 'estado')
        }),
        ('Documento', {
            'fields': ('filename', 'file', 'removed')
        }),
        ('Tipos y Estados', {
            'fields': ('doctype_obj', 'doctype_legacy', 'life_cycle_state_obj', 'life_cycle_state_legacy', 'life_cycle_state_date')
        }),
        ('Organización', {
            'fields': ('serie',)
        }),
        ('Metadatos', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('features_display',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['marcar_no_removido', 'marcar_removido', 'exportar_metadata']
    
    def titulo_display(self, obj):
        if obj.removed:
            return format_html('<span style="text-decoration: line-through; color: #999;">{}</span>', obj.titulo)
        return obj.titulo
    titulo_display.short_description = 'Título'
    titulo_display.admin_order_field = 'titulo'
    
    def doctype_display(self, obj):
        if obj.doctype_obj:
            color = '#2196F3' if obj.doctype_obj.name == 'acta' else '#4CAF50'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.doctype_obj.label or obj.doctype_obj.name
            )
        return format_html('<span style="color: #999;">{}</span>', obj.doctype_legacy or 'Sin tipo')
    doctype_display.short_description = 'Tipo'
    doctype_display.admin_order_field = 'doctype_obj__name'
    
    def lifecycle_state_display(self, obj):
        if obj.life_cycle_state_obj:
            colors = {
                'Pendiente Firma OTP': '#FF9800',
                'Firmada': '#4CAF50',
                'Rechazada': '#F44336',
                'Pendiente Blockchain': '#2196F3',
                'Fallo en Blockchain': '#F44336'
            }
            color = colors.get(obj.life_cycle_state_obj.name, '#666')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.life_cycle_state_obj.name
            )
        return format_html('<span style="color: #999;">{}</span>', obj.life_cycle_state_legacy or 'Sin estado')
    lifecycle_state_display.short_description = 'Estado'
    lifecycle_state_display.admin_order_field = 'life_cycle_state_obj__name'
    
    def removed_badge(self, obj):
        if obj.removed:
            return format_html('<span style="background-color: #F44336; color: white; padding: 2px 6px; border-radius: 3px;">Eliminado</span>')
        return format_html('<span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px;">Activo</span>')
    removed_badge.short_description = 'Estado'
    removed_badge.admin_order_field = 'removed'
    
    def metadata_display(self, obj):
        if obj._metadata_cache:
            return format_html('<pre style="max-height: 300px; overflow-y: auto;">{}</pre>', 
                             json.dumps(obj._metadata_cache, indent=2, ensure_ascii=False))
        return 'Sin metadatos'
    metadata_display.short_description = 'Metadatos (JSON)'
    
    def features_display(self, obj):
        if obj._features_cache:
            return format_html('<pre style="max-height: 300px; overflow-y: auto;">{}</pre>', 
                             json.dumps(obj._features_cache, indent=2, ensure_ascii=False))
        return 'Sin features'
    features_display.short_description = 'Features (JSON)'
    
    def marcar_no_removido(self, request, queryset):
        updated = queryset.filter(removed=True).update(removed=False)
        self.message_user(request, f'{updated} archivos marcados como no eliminados.')
    marcar_no_removido.short_description = "Marcar como no eliminados"
    
    def marcar_removido(self, request, queryset):
        updated = queryset.filter(removed=False).update(removed=True)
        self.message_user(request, f'{updated} archivos marcados como eliminados.')
    marcar_removido.short_description = "Marcar como eliminados"
    
    def exportar_metadata(self, request, queryset):
        # Acción para exportar metadata (placeholder)
        self.message_user(request, f'Exportando metadata de {queryset.count()} archivos...')
    exportar_metadata.short_description = "Exportar metadata"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('doctype_obj', 'life_cycle_state_obj', 'serie')






















