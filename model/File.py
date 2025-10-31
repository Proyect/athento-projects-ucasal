"""
Mock mejorado del modelo File para testing sin Athento
Mantiene compatibilidad con el código existente y agrega funcionalidad para operations
"""
from django.db import models
from django.utils import timezone
from django.core.files.base import ContentFile
import uuid
import os


class Doctype(models.Model):
    """Mock del doctype de Athento"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100, default='')
    
    class Meta:
        managed = True
        db_table = 'doctype_doctype'
        verbose_name = 'Doctype'
        verbose_name_plural = 'Doctypes'
    
    def __str__(self):
        return self.label or self.name
    
    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.name.replace('_', ' ').title()
        super().save(*args, **kwargs)


class LifeCycleState(models.Model):
    """Mock del estado del ciclo de vida"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    maximum_time = models.IntegerField(null=True, blank=True, help_text='SLA en minutos')
    
    class Meta:
        managed = True
        db_table = 'lifecycle_state'
        verbose_name = 'Lifecycle State'
        verbose_name_plural = 'Lifecycle States'
    
    def __str__(self):
        return self.name


class Team(models.Model):
    """Mock del Team de Athento"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=200, default='')
    
    class Meta:
        managed = True
        db_table = 'team_team'
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
    
    def __str__(self):
        return self.label or self.name
    
    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.name.replace('_', ' ').title()
        super().save(*args, **kwargs)


class Serie(models.Model):
    """Mock del Serie (Espacio) de Athento"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=200, default='')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='serie_set')
    
    class Meta:
        managed = True
        db_table = 'series_serie'
        verbose_name = 'Serie'
        verbose_name_plural = 'Series'
    
    def __str__(self):
        return self.label or self.name
    
    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.name.replace('_', ' ').title()
        super().save(*args, **kwargs)


class File(models.Model):
    """
    Modelo File mejorado para gestión de documentos
    Compatible con código existente y operations de Athento
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=200)
    estado = models.CharField(max_length=50, default='recibida')
    
    # Campos legacy (compatibilidad con código existente)
    # Nota: db_column no se usa aquí porque la migración 0002 ya renombró las columnas
    doctype_legacy = models.CharField(max_length=50, default='acta')
    life_cycle_state_legacy = models.CharField(max_length=50, default='recibida')
    
    # Relaciones con objetos mock (para operations)
    doctype_obj = models.ForeignKey(
        Doctype, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='files',
        db_column='doctype_id'
    )
    life_cycle_state_obj = models.ForeignKey(
        LifeCycleState, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='files',
        db_column='life_cycle_state_id'
    )
    serie = models.ForeignKey(
        Serie, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='files',
        db_column='serie_id'
    )
    
    filename = models.CharField(max_length=255, default='documento.pdf')
    file = models.FileField(upload_to='documents/', null=True, blank=True)
    removed = models.BooleanField(default=False)
    
    # Campos para almacenar metadata y features dinámicamente
    _metadata_cache = models.JSONField(default=dict, blank=True, null=True)
    _features_cache = models.JSONField(default=dict, blank=True, null=True)
    
    life_cycle_state_date = models.DateTimeField(default=timezone.now)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = True
        db_table = 'file_file'
        verbose_name = 'File'
        verbose_name_plural = 'Files'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.titulo
    
    @property
    def doctype(self):
        """
        Property que retorna objeto Doctype si existe, sino un mock object con .name
        Para compatibilidad con código existente y operations
        """
        if self.doctype_obj:
            return self.doctype_obj
        
        # Crear objeto mock para compatibilidad
        class MockDoctype:
            def __init__(self, name):
                self.name = name
                self.label = name.replace('_', ' ').title()
                self.uuid = None
        return MockDoctype(self.doctype_legacy)
    
    @doctype.setter
    def doctype(self, value):
        """Setter para doctype"""
        if isinstance(value, str):
            self.doctype_legacy = value
            # Intentar obtener objeto si existe
            try:
                self.doctype_obj = Doctype.objects.get(name=value)
            except Doctype.DoesNotExist:
                self.doctype_obj = None
        elif isinstance(value, Doctype):
            self.doctype_obj = value
            self.doctype_legacy = value.name
        else:
            # Objeto mock
            self.doctype_legacy = value.name if hasattr(value, 'name') else str(value)
            self.doctype_obj = None
    
    @property
    def life_cycle_state(self):
        """
        Property que retorna objeto LifeCycleState si existe, sino un mock object con .name
        Para compatibilidad con código existente y operations
        """
        if self.life_cycle_state_obj:
            return self.life_cycle_state_obj
        
        # Crear objeto mock para compatibilidad
        class MockState:
            def __init__(self, name):
                self.name = name
                self.uuid = None
                self.maximum_time = None
        return MockState(self.life_cycle_state_legacy)
    
    @life_cycle_state.setter
    def life_cycle_state(self, value):
        """Setter para life_cycle_state"""
        if isinstance(value, str):
            self.life_cycle_state_legacy = value
            self.life_cycle_state_date = timezone.now()
            # Intentar obtener objeto si existe
            try:
                self.life_cycle_state_obj = LifeCycleState.objects.get(name=value)
            except LifeCycleState.DoesNotExist:
                self.life_cycle_state_obj = None
        elif isinstance(value, LifeCycleState):
            self.life_cycle_state_obj = value
            self.life_cycle_state_legacy = value.name
            self.life_cycle_state_date = timezone.now()
        else:
            # Objeto mock
            name = value.name if hasattr(value, 'name') else str(value)
            self.life_cycle_state_legacy = name
            self.life_cycle_state_date = timezone.now()
            try:
                self.life_cycle_state_obj = LifeCycleState.objects.get(name=name)
            except LifeCycleState.DoesNotExist:
                self.life_cycle_state_obj = None
    
    def gmv(self, key):
        """
        Get metadata value - mejorado
        Primero busca en _metadata_cache, luego en atributos del modelo
        """
        # Inicializar cache si no existe
        if self._metadata_cache is None:
            self._metadata_cache = {}
        
        # Buscar en cache primero
        if key in self._metadata_cache:
            value = self._metadata_cache[key]
            # Convertir None string a None real
            return None if value == 'None' or value is None else value
        
        # Buscar como atributo del modelo
        field_name = key.replace('metadata.', '')
        if hasattr(self, field_name):
            value = getattr(self, field_name)
            return None if value == 'None' or value is None else value
        
        return None
    
    def gfv(self, key):
        """
        Get feature value - mejorado
        Primero busca en _features_cache, luego en atributos del modelo
        """
        # Inicializar cache si no existe
        if self._features_cache is None:
            self._features_cache = {}
        
        # Buscar en cache primero
        if key in self._features_cache:
            value = self._features_cache[key]
            return None if value == 'None' or value is None else value
        
        # Buscar como atributo del modelo
        field_name = key.replace('.', '_')
        if hasattr(self, field_name):
            value = getattr(self, field_name)
            return None if value == 'None' or value is None else value
        
        return None
    
    def set_metadata(self, key, value, overwrite=False):
        """
        Set metadata value - mejorado
        Guarda en _metadata_cache y también como atributo si existe el campo
        """
        if self._metadata_cache is None:
            self._metadata_cache = {}
        
        if not overwrite and key in self._metadata_cache:
            return
        
        self._metadata_cache[key] = value
        
        # También intentar setear como atributo si existe el campo
        field_name = key.replace('metadata.', '')
        if hasattr(self, field_name):
            try:
                setattr(self, field_name, value)
            except (AttributeError, ValueError):
                pass  # Ignorar si no se puede setear
        
        # Guardar solo el cache, no todos los campos
        self.save(update_fields=['_metadata_cache'])
    
    def set_feature(self, key, value):
        """
        Set feature value - mejorado
        Guarda en _features_cache y también como atributo si existe el campo
        """
        if self._features_cache is None:
            self._features_cache = {}
        
        self._features_cache[key] = value
        
        # También intentar setear como atributo si existe el campo
        field_name = key.replace('.', '_')
        if hasattr(self, field_name):
            try:
                setattr(self, field_name, value)
            except (AttributeError, ValueError):
                pass  # Ignorar si no se puede setear
        
        # Guardar solo el cache, no todos los campos
        self.save(update_fields=['_features_cache'])
    
    def change_life_cycle_state(self, new_state):
        """
        Cambiar estado del ciclo de vida
        Acepta string o objeto LifeCycleState
        """
        if isinstance(new_state, str):
            state, created = LifeCycleState.objects.get_or_create(name=new_state)
            if created:
                # Guardar el objeto recién creado
                state.save()
        elif isinstance(new_state, LifeCycleState):
            state = new_state
        else:
            # Objeto mock, obtener por nombre
            name = new_state.name if hasattr(new_state, 'name') else str(new_state)
            state, _ = LifeCycleState.objects.get_or_create(name=name)
        
        self.life_cycle_state_obj = state
        self.life_cycle_state_legacy = state.name
        self.life_cycle_state_date = timezone.now()
        self.save(update_fields=['life_cycle_state_obj', 'life_cycle_state_legacy', 'life_cycle_state_date'])
    
    def move_to_serie(self, serie):
        """
        Mover documento a una serie
        Acepta string (nombre) o objeto Serie
        """
        if isinstance(serie, str):
            try:
                serie_obj = Serie.objects.get(name=serie)
            except Serie.DoesNotExist:
                raise ValueError(f"Serie '{serie}' no existe. Crea la serie primero.")
        elif isinstance(serie, Serie):
            serie_obj = serie
        else:
            raise ValueError(f"Tipo inválido para serie: {type(serie)}")
        
        self.serie = serie_obj
        self.save(update_fields=['serie'])
    
    def update_binary(self, file_obj, filename):
        """Update binary file"""
        self.file = file_obj
        self.filename = filename
        self.save(update_fields=['file', 'filename'])
    
    @property
    def file_path(self):
        """
        Retorna el path del archivo
        Si no existe el archivo físico, crea uno temporal para testing
        """
        if self.file and os.path.exists(self.file.path):
            return self.file.path
        
        # Para testing, crear un archivo temporal si no existe
        from django.conf import settings
        
        # Contenido PDF mínimo válido
        test_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n/Root 1 0 R\n>>\nstartxref\n0\n%%EOF'
        
        if not self.file:
            # Crear archivo temporal
            file_name = self.filename or f'test_{self.uuid}.pdf'
            media_root = getattr(settings, 'MEDIA_ROOT', 'media')
            os.makedirs(os.path.join(media_root, 'documents'), exist_ok=True)
            file_path = os.path.join(media_root, 'documents', file_name)
            
            with open(file_path, 'wb') as f:
                f.write(test_pdf_content)
            
            # Guardar referencia en el modelo
            self.file.name = f'documents/{file_name}'
            self.save(update_fields=['file'])
        
        return self.file.path if self.file else None


class TituloFileManager(models.Manager):
    def get_queryset(self):
        # Filtrar por doctype 'títulos' considerando ambos campos (legacy y FK)
        from django.db.models import Q
        return super().get_queryset().filter(
            Q(doctype_legacy='títulos') | Q(doctype_obj__name='títulos')
        )


class TituloFile(File):
    """Proxy para listar únicamente documentos de doctype 'títulos' en el admin."""
    objects = TituloFileManager()

    class Meta:
        proxy = True
        verbose_name = 'Título'
        verbose_name_plural = 'Títulos'
