from django.contrib import admin
from model.File import TituloFile


@admin.register(TituloFile)
class TituloAdmin(admin.ModelAdmin):
    list_display = [
        'uuid',
        'titulo',
        'life_cycle_state_legacy',
        'filename',
        'created_at',
        'updated_at',
        'removed',
    ]

    list_filter = [
        'life_cycle_state_legacy',
        'removed',
        'serie',
    ]

    search_fields = [
        'uuid',
        'titulo',
        'filename',
    ]

    readonly_fields = [
        'uuid',
        'created_at',
        'updated_at',
        'doctype_legacy',
        'life_cycle_state_legacy',
        'filename',
        'file',
    ]

    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'titulo')
        }),
        ('Documento', {
            'fields': ('filename', 'file')
        }),
        ('Ciclo de Vida', {
            'fields': ('life_cycle_state_legacy', 'created_at', 'updated_at')
        }),
        ('Metadatos', {
            'fields': ('doctype_legacy', 'serie', 'removed')
        }),
    )

    def get_queryset(self, request):
        # Asegurar que sólo se muestren títulos (el manager ya filtra)
        return super().get_queryset(request)



