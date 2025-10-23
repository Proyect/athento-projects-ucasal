"""
Mock del modelo File para testing
"""
from django.db import models
import uuid

class File(models.Model):
    """Modelo File para gestión de documentos"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=200)
    estado = models.CharField(max_length=50, default='recibida')
    doctype = models.CharField(max_length=50, default='acta')
    life_cycle_state = models.CharField(max_length=50, default='recibida')
    filename = models.CharField(max_length=255, default='documento.pdf')
    file = models.FileField(upload_to='documents/', null=True, blank=True)
    removed = models.BooleanField(default=False)
    
    class Meta:
        managed = True  # Django gestiona la tabla
        db_table = 'file_file'
    
    def __str__(self):
        return self.titulo
    
    def gmv(self, key):
        """Get metadata value - mock implementation"""
        return getattr(self, key.replace('metadata.', ''), None)
    
    def gfv(self, key):
        """Get feature value - mock implementation"""
        return getattr(self, key.replace('.', '_'), None)
    
    def set_metadata(self, key, value, overwrite=False):
        """Set metadata value - mock implementation"""
        field_name = key.replace('metadata.', '')
        if hasattr(self, field_name):
            setattr(self, field_name, value)
    
    def set_feature(self, key, value):
        """Set feature value - mock implementation"""
        field_name = key.replace('.', '_')
        setattr(self, field_name, value)
    
    def change_life_cycle_state(self, new_state):
        """Change life cycle state - mock implementation"""
        self.life_cycle_state = new_state
        self.save()
    
    def update_binary(self, file_obj, filename):
        """Update binary file - mock implementation"""
        self.file = file_obj
        self.filename = filename
        self.save()


