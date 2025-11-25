from django.contrib import admin
from django.utils.html import format_html
from model.File import TituloFile
import json


@admin.register(TituloFile)
class TituloAdmin(admin.ModelAdmin):
    list_display = [
        'titulo',
        'lifecycle_state_colored',
        'serie',
        'filename',
        'created_at',
        'removed_badge',
        'uuid_short'
    ]

    list_filter = [
        'life_cycle_state_obj',
        'life_cycle_state_legacy',
        'removed',
        'serie',
        'created_at',
        'updated_at'
    ]

    search_fields = [
        'uuid',
        'titulo',
        'filename',
        'life_cycle_state_legacy'
    ]

    readonly_fields = [
        'uuid',
        'created_at',
        'updated_at',
        'life_cycle_state_date',
        'doctype_legacy',
        'life_cycle_state_legacy',
        'filename',
        'file',
        'metadata_display',
        'features_display'
    ]

    date_hierarchy = 'created_at'

    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'titulo', 'estado')
        }),
        ('Documento', {
            'fields': ('filename', 'file', 'removed')
        }),
        ('Ciclo de Vida', {
            'fields': ('life_cycle_state_obj', 'life_cycle_state_legacy', 'life_cycle_state_date')
        }),
        ('Organización', {
            'fields': ('doctype_legacy', 'serie')
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
    
    actions = [
        'marcar_no_removido',
        'marcar_removido',
        'cambiar_estado_recibido',
        'cambiar_estado_pendiente_aprobacion_ua',
        'exportar_titulos'
    ]

    def uuid_short(self, obj):
        return str(obj.uuid)[:8] + '...'
    uuid_short.short_description = 'UUID'
    uuid_short.admin_order_field = 'uuid'

    def lifecycle_state_colored(self, obj):
        if obj.life_cycle_state_obj:
            colors = {
                'Recibido': '#2196F3',
                'Pendiente Aprobación UA': '#FF9800',
                'Aprobado por UA': '#4CAF50',
                'Pendiente Aprobación R': '#FF9800',
                'Aprobado por R': '#4CAF50',
                'Pendiente Firma SG': '#9C27B0',
                'Firmado por SG': '#4CAF50',
                'Pendiente Blockchain': '#2196F3',
                'Registrado en Blockchain': '#4CAF50',
                'Título Emitido': '#4CAF50',
                'Rechazado': '#F44336'
            }
            color = colors.get(obj.life_cycle_state_obj.name, '#666')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.life_cycle_state_obj.name
            )
        return format_html('<span style="color: #999;">{}</span>', obj.life_cycle_state_legacy or 'Sin estado')
    lifecycle_state_colored.short_description = 'Estado'
    lifecycle_state_colored.admin_order_field = 'life_cycle_state_obj__name'

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
        self.message_user(request, f'{updated} títulos marcados como no eliminados.')
    marcar_no_removido.short_description = "✅ Marcar como no eliminados"

    def marcar_removido(self, request, queryset):
        updated = queryset.filter(removed=False).update(removed=True)
        self.message_user(request, f'{updated} títulos marcados como eliminados.')
    marcar_removido.short_description = "🚫 Marcar como eliminados"

    def cambiar_estado_recibido(self, request, queryset):
        from ucasal.utils import TituloStates
        from model.File import LifeCycleState
        estado, _ = LifeCycleState.objects.get_or_create(name=TituloStates.recibido)
        updated = 0
        for titulo in queryset:
            titulo.change_life_cycle_state(estado)
            updated += 1
        self.message_user(request, f'{updated} títulos cambiados a estado "Recibido".')
    cambiar_estado_recibido.short_description = "📥 Cambiar a Recibido"

    def cambiar_estado_pendiente_aprobacion_ua(self, request, queryset):
        from ucasal.utils import TituloStates
        from model.File import LifeCycleState
        estado, _ = LifeCycleState.objects.get_or_create(name=TituloStates.pendiente_aprobacion_ua)
        updated = 0
        for titulo in queryset:
            titulo.change_life_cycle_state(estado)
            updated += 1
        self.message_user(request, f'{updated} títulos cambiados a estado "Pendiente Aprobación UA".')
    cambiar_estado_pendiente_aprobacion_ua.short_description = "⏳ Cambiar a Pendiente UA"

    def exportar_titulos(self, request, queryset):
        """Exportar información básica de títulos seleccionados"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="titulos_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['UUID', 'Título', 'Estado', 'Serie', 'Filename', 'Fecha Creación'])
        
        for titulo in queryset:
            writer.writerow([
                str(titulo.uuid),
                titulo.titulo,
                titulo.life_cycle_state_legacy or 'Sin estado',
                titulo.serie.name if titulo.serie else 'Sin serie',
                titulo.filename,
                titulo.created_at.strftime('%Y-%m-%d %H:%M:%S') if titulo.created_at else ''
            ])
        
        return response
    exportar_titulos.short_description = "📥 Exportar a CSV"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('doctype_obj', 'life_cycle_state_obj', 'serie')



