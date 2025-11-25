from django.contrib import admin
from django.utils.html import format_html
from .models import Acta

@admin.register(Acta)
class ActaAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 
        'docente_asignado', 
        'codigo_sector', 
        'estado_coloreado', 
        'fecha_creacion',
        'es_revision_display',
        'activa'
    ]
    
    list_filter = [
        'estado',
        'activa',
        'firmada_con_otp',
        'codigo_sector',
        'fecha_creacion',
        'fecha_firma',
        'numero_revision',
        ('docente_asignado', admin.EmptyFieldListFilter)
    ]
    
    search_fields = [
        'titulo',
        'docente_asignado',
        'nombre_docente',
        'codigo_sector',
        'uuid'
    ]
    
    readonly_fields = [
        'uuid',
        'fecha_creacion',
        'fecha_modificacion',
        'hash_documento',
        'link_file_display'
    ]
    
    def link_file_display(self, obj):
        """Mostrar enlace al File relacionado si existe"""
        from model.File import File
        try:
            file_obj = File.objects.get(uuid=obj.uuid)
            url = reverse('admin:model_file_change', args=[file_obj.uuid])
            return format_html('<a href="{}">Ver archivo relacionado (UUID: {})</a>', url, str(file_obj.uuid)[:8])
        except File.DoesNotExist:
            return format_html('<span style="color: #999;">No hay archivo relacionado</span>')
    link_file_display.short_description = 'Archivo relacionado'
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('uuid', 'titulo', 'descripcion', 'estado', 'activa')
        }),
        ('Información del Docente', {
            'fields': ('docente_asignado', 'nombre_docente')
        }),
        ('Información Académica', {
            'fields': ('codigo_sector', 'numero_revision', 'uuid_acta_previa')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_firma', 'fecha_rechazo', 'fecha_modificacion')
        }),
        ('Información de Firma', {
            'fields': ('firmada_con_otp', 'ip_firma', 'latitud', 'longitud', 'precision_gps', 'user_agent')
        }),
        ('Blockchain', {
            'fields': ('registro_blockchain', 'hash_documento')
        }),
        ('Rechazo', {
            'fields': ('motivo_rechazo',),
            'classes': ('collapse',)
        })
    )
    
    def estado_coloreado(self, obj):
        color = obj.get_estado_display_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_coloreado.short_description = 'Estado'
    estado_coloreado.admin_order_field = 'estado'
    
    def es_revision_display(self, obj):
        if obj.es_revision():
            return format_html(
                '<span style="background-color: #ffeb3b; padding: 2px 6px; border-radius: 3px;">Revisión #{}</span>',
                obj.numero_revision
            )
        return format_html('<span style="color: #666;">Original</span>')
    es_revision_display.short_description = 'Tipo'
    es_revision_display.admin_order_field = 'numero_revision'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def has_add_permission(self, request):
        return True
    
    def has_change_permission(self, request, obj=None):
        return True
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    date_hierarchy = 'fecha_creacion'
    
    actions = [
        'marcar_como_firmada', 
        'marcar_como_rechazada', 
        'reactivar_acta',
        'cambiar_estado_recibida',
        'cambiar_estado_pendiente_otp',
        'desactivar_actas',
        'activar_actas',
        'exportar_actas'
    ]
    
    def marcar_como_firmada(self, request, queryset):
        updated = queryset.filter(estado__in=['pendiente_otp', 'pendiente_blockchain']).update(
            estado='firmada',
            firmada_con_otp=True
        )
        self.message_user(request, f'{updated} actas marcadas como firmadas.')
    marcar_como_firmada.short_description = "✅ Marcar como firmadas"
    
    def marcar_como_rechazada(self, request, queryset):
        updated = queryset.filter(estado='pendiente_otp').update(
            estado='rechazada',
            motivo_rechazo='Rechazada desde el admin'
        )
        self.message_user(request, f'{updated} actas marcadas como rechazadas.')
    marcar_como_rechazada.short_description = "❌ Marcar como rechazadas"
    
    def reactivar_acta(self, request, queryset):
        updated = queryset.filter(estado='rechazada').update(
            estado='pendiente_otp',
            motivo_rechazo=''
        )
        self.message_user(request, f'{updated} actas reactivadas.')
    reactivar_acta.short_description = "🔄 Reactivar actas rechazadas"
    
    def cambiar_estado_recibida(self, request, queryset):
        updated = queryset.update(estado='recibida')
        self.message_user(request, f'{updated} actas cambiadas a estado "Recibida".')
    cambiar_estado_recibida.short_description = "📥 Cambiar a Recibida"
    
    def cambiar_estado_pendiente_otp(self, request, queryset):
        updated = queryset.update(estado='pendiente_otp')
        self.message_user(request, f'{updated} actas cambiadas a estado "Pendiente OTP".')
    cambiar_estado_pendiente_otp.short_description = "⏳ Cambiar a Pendiente OTP"
    
    def desactivar_actas(self, request, queryset):
        updated = queryset.filter(activa=True).update(activa=False)
        self.message_user(request, f'{updated} actas desactivadas.')
    desactivar_actas.short_description = "🚫 Desactivar actas"
    
    def activar_actas(self, request, queryset):
        updated = queryset.filter(activa=False).update(activa=True)
        self.message_user(request, f'{updated} actas activadas.')
    activar_actas.short_description = "✅ Activar actas"
    
    def exportar_actas(self, request, queryset):
        """Exportar información básica de actas seleccionadas"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="actas_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['UUID', 'Título', 'Docente', 'Estado', 'Código Sector', 'Fecha Creación'])
        
        for acta in queryset:
            writer.writerow([
                str(acta.uuid),
                acta.titulo,
                acta.docente_asignado,
                acta.get_estado_display(),
                acta.codigo_sector,
                acta.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    exportar_actas.short_description = "📥 Exportar a CSV"

