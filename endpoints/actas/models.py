from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
import re

class Acta(models.Model):
    """Modelo para gestionar actas de examen"""
    
    ESTADOS_CHOICES = [
        ('recibida', 'Recibida'),
        ('pendiente_otp', 'Pendiente Firma OTP'),
        ('pendiente_blockchain', 'Pendiente Blockchain'),
        ('firmada', 'Firmada'),
        ('fallo_blockchain', 'Fallo en Blockchain'),
        ('rechazada', 'Rechazada'),
    ]
    
    # Campos principales
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True)
    titulo = models.CharField(max_length=200, verbose_name="Título del Acta")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    
    # Información del docente
    docente_asignado = models.EmailField(
        verbose_name="Email del Docente Asignado",
        validators=[EmailValidator(message="Ingrese un email válido")]
    )
    nombre_docente = models.CharField(
        max_length=100, 
        verbose_name="Nombre del Docente",
        validators=[
            RegexValidator(
                regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\.]+$',
                message="El nombre solo puede contener letras, espacios y puntos"
            )
        ]
    )
    
    # Información académica
    codigo_sector = models.CharField(
        max_length=10, 
        verbose_name="Código de Sector",
        validators=[
            RegexValidator(
                regex=r'^\d{3}$',
                message="El código de sector debe ser un número de 3 dígitos"
            )
        ]
    )
    numero_revision = models.IntegerField(default=0, verbose_name="Número de Revisión")
    uuid_acta_previa = models.UUIDField(blank=True, null=True, verbose_name="UUID Acta Previa")
    
    # Estados y fechas
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='recibida', verbose_name="Estado")
    fecha_creacion = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Creación")
    fecha_firma = models.DateField(blank=True, null=True, verbose_name="Fecha de Firma")
    fecha_rechazo = models.DateField(blank=True, null=True, verbose_name="Fecha de Rechazo")
    motivo_rechazo = models.TextField(blank=True, null=True, verbose_name="Motivo de Rechazo")
    
    # Información técnica
    firmada_con_otp = models.BooleanField(default=False, verbose_name="Firmada con OTP")
    registro_blockchain = models.CharField(max_length=20, blank=True, null=True, verbose_name="Registro en Blockchain")
    hash_documento = models.CharField(max_length=64, blank=True, null=True, verbose_name="Hash del Documento")
    
    # Metadatos adicionales
    ip_firma = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP de Firma")
    latitud = models.FloatField(blank=True, null=True, verbose_name="Latitud")
    longitud = models.FloatField(blank=True, null=True, verbose_name="Longitud")
    precision_gps = models.CharField(max_length=50, blank=True, null=True, verbose_name="Precisión GPS")
    user_agent = models.TextField(blank=True, null=True, verbose_name="User Agent")
    
    # Campos de control
    activa = models.BooleanField(default=True, verbose_name="Activa")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        verbose_name = "Acta"
        verbose_name_plural = "Actas"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', 'activa'], name='acta_estado_activa_idx'),
            models.Index(fields=['docente_asignado'], name='acta_docente_idx'),
            models.Index(fields=['fecha_creacion'], name='acta_fecha_creacion_idx'),
            models.Index(fields=['fecha_firma'], name='acta_fecha_firma_idx'),
            models.Index(fields=['uuid_acta_previa'], name='acta_uuid_previa_idx'),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.docente_asignado} ({self.estado})"
    
    def get_estado_display_color(self):
        """Retorna el color CSS para el estado"""
        colors = {
            'recibida': 'blue',
            'pendiente_otp': 'orange',
            'pendiente_blockchain': 'yellow',
            'firmada': 'green',
            'fallo_blockchain': 'red',
            'rechazada': 'red',
        }
        return colors.get(self.estado, 'gray')
    
    def es_revision(self):
        """Indica si esta acta es una revisión de otra"""
        return self.numero_revision > 0
    
    def puede_firmar(self):
        """Indica si la acta puede ser firmada"""
        return self.estado in ['pendiente_otp', 'fallo_blockchain']
    
    def puede_rechazar(self):
        """Indica si la acta puede ser rechazada"""
        return self.estado == 'pendiente_otp'
    
    def clean(self):
        """Validaciones personalizadas del modelo"""
        super().clean()
        
        # Validar que si es revisión, tenga UUID de acta previa
        if self.es_revision() and not self.uuid_acta_previa:
            raise ValidationError({
                'uuid_acta_previa': 'Las actas de revisión deben tener un UUID de acta previa.'
            })
        
        # Validar que si es revisión, la acta previa exista
        if self.es_revision() and self.uuid_acta_previa:
            try:
                acta_previa = Acta.objects.get(uuid=self.uuid_acta_previa)
                if acta_previa.numero_revision >= self.numero_revision:
                    raise ValidationError({
                        'numero_revision': 'El número de revisión debe ser mayor al de la acta previa.'
                    })
            except Acta.DoesNotExist:
                raise ValidationError({
                    'uuid_acta_previa': 'La acta previa especificada no existe.'
                })
        
        # Validar fechas
        if self.fecha_firma and self.fecha_rechazo:
            raise ValidationError({
                'fecha_firma': 'Una acta no puede estar firmada y rechazada al mismo tiempo.',
                'fecha_rechazo': 'Una acta no puede estar firmada y rechazada al mismo tiempo.'
            })
        
        # Validar que si está firmada, tenga fecha de firma
        if self.estado == 'firmada' and not self.fecha_firma:
            self.fecha_firma = timezone.now().date()
        
        # Validar que si está rechazada, tenga motivo
        if self.estado == 'rechazada' and not self.motivo_rechazo:
            raise ValidationError({
                'motivo_rechazo': 'Las actas rechazadas deben tener un motivo de rechazo.'
            })
        
        # Validar coordenadas GPS
        if self.latitud is not None and (self.latitud < -90 or self.latitud > 90):
            raise ValidationError({
                'latitud': 'La latitud debe estar entre -90 y 90 grados.'
            })
        
        if self.longitud is not None and (self.longitud < -180 or self.longitud > 180):
            raise ValidationError({
                'longitud': 'La longitud debe estar entre -180 y 180 grados.'
            })
    
    def save(self, *args, **kwargs):
        """Override save para ejecutar validaciones"""
        self.clean()
        super().save(*args, **kwargs)
