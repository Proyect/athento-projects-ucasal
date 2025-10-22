"""
Mock del modelo File para testing
"""
from django.db import models
import uuid

class File(models.Model):
    """Mock del modelo File para testing"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=200)
    estado = models.CharField(max_length=50, default='recibida')
    
    class Meta:
        managed = False  # No crear tabla en la base de datos
        db_table = 'file_file'  # Nombre de tabla ficticio
    
    def __str__(self):
        return self.titulo


