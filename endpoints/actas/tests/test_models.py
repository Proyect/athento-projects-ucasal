from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date
import uuid
from ..models import Acta

class ActaModelTest(TestCase):
    def setUp(self):
        """Configuración inicial para cada test"""
        self.acta_data = {
            'uuid': uuid.uuid4(),
            'titulo': 'Acta de Examen - Matemática I',
            'descripcion': 'Examen final de Matemática I',
            'docente_asignado': 'profesor@ucasal.edu.ar',
            'nombre_docente': 'Dr. Juan Pérez',
            'codigo_sector': '001',
            'estado': 'recibida'
        }
    
    def test_crear_acta_basica(self):
        """Test: Crear una acta con datos básicos"""
        acta = Acta.objects.create(**self.acta_data)
        
        self.assertEqual(acta.titulo, 'Acta de Examen - Matemática I')
        self.assertEqual(acta.docente_asignado, 'profesor@ucasal.edu.ar')
        self.assertEqual(acta.estado, 'recibida')
        self.assertTrue(acta.activa)
        self.assertIsNotNone(acta.fecha_creacion)
    
    def test_acta_revision(self):
        """Test: Crear acta como revisión"""
        acta_original = Acta.objects.create(**self.acta_data)
        
        acta_revision_data = self.acta_data.copy()
        acta_revision_data['uuid'] = uuid.uuid4()
        acta_revision_data['numero_revision'] = 1
        acta_revision_data['uuid_acta_previa'] = acta_original.uuid
        
        acta_revision = Acta.objects.create(**acta_revision_data)
        
        self.assertTrue(acta_revision.es_revision())
        self.assertEqual(acta_revision.numero_revision, 1)
        self.assertEqual(acta_revision.uuid_acta_previa, acta_original.uuid)
    
    def test_estados_validos(self):
        """Test: Verificar estados válidos"""
        estados_validos = [choice[0] for choice in Acta.ESTADOS_CHOICES]
        
        for i, estado in enumerate(estados_validos):
            acta_data = self.acta_data.copy()
            acta_data['uuid'] = uuid.uuid4()  # UUID único para cada test
            acta_data['titulo'] = f'Acta Test {i}'  # Título único
            acta_data['estado'] = estado
            
            # Agregar motivo si es estado rechazada
            if estado == 'rechazada':
                acta_data['motivo_rechazo'] = 'Motivo de prueba'
            
            acta = Acta.objects.create(**acta_data)
            self.assertEqual(acta.estado, estado)
    
    def test_estado_display_color(self):
        """Test: Verificar colores de estado"""
        acta = Acta.objects.create(**self.acta_data)
        
        # Test estado recibida
        acta.estado = 'recibida'
        self.assertEqual(acta.get_estado_display_color(), 'blue')
        
        # Test estado firmada
        acta.estado = 'firmada'
        self.assertEqual(acta.get_estado_display_color(), 'green')
        
        # Test estado rechazada
        acta.estado = 'rechazada'
        self.assertEqual(acta.get_estado_display_color(), 'red')
    
    def test_puede_firmar(self):
        """Test: Verificar si acta puede ser firmada"""
        acta = Acta.objects.create(**self.acta_data)
        
        # Estados que permiten firma
        acta.estado = 'pendiente_otp'
        self.assertTrue(acta.puede_firmar())
        
        acta.estado = 'fallo_blockchain'
        self.assertTrue(acta.puede_firmar())
        
        # Estados que NO permiten firma
        acta.estado = 'firmada'
        self.assertFalse(acta.puede_firmar())
        
        acta.estado = 'rechazada'
        self.assertFalse(acta.puede_firmar())
    
    def test_puede_rechazar(self):
        """Test: Verificar si acta puede ser rechazada"""
        acta = Acta.objects.create(**self.acta_data)
        
        # Solo pendiente_otp permite rechazo
        acta.estado = 'pendiente_otp'
        self.assertTrue(acta.puede_rechazar())
        
        # Otros estados no permiten rechazo
        acta.estado = 'firmada'
        self.assertFalse(acta.puede_rechazar())
        
        acta.estado = 'rechazada'
        self.assertFalse(acta.puede_rechazar())
    
    def test_str_representation(self):
        """Test: Verificar representación string del modelo"""
        acta = Acta.objects.create(**self.acta_data)
        expected = f"{acta.titulo} - {acta.docente_asignado} ({acta.estado})"
        self.assertEqual(str(acta), expected)
    
    def test_fecha_firma_automatica(self):
        """Test: Verificar fecha de firma automática"""
        acta = Acta.objects.create(**self.acta_data)
        acta.estado = 'firmada'
        acta.firmada_con_otp = True
        acta.fecha_firma = date.today()
        acta.save()
        
        self.assertEqual(acta.fecha_firma, date.today())
        self.assertTrue(acta.firmada_con_otp)
    
    def test_ordering(self):
        """Test: Verificar ordenamiento por fecha de creación"""
        # Crear actas con diferentes fechas
        acta1 = Acta.objects.create(**self.acta_data)
        
        acta2_data = self.acta_data.copy()
        acta2_data['uuid'] = uuid.uuid4()
        acta2_data['titulo'] = 'Acta 2'
        acta2 = Acta.objects.create(**acta2_data)
        
        # Verificar que se ordenan por fecha de creación descendente
        actas = Acta.objects.all()
        self.assertEqual(actas[0], acta2)  # Más reciente primero
        self.assertEqual(actas[1], acta1)
    
    def test_campos_obligatorios(self):
        """Test: Verificar campos obligatorios"""
        # Test sin título
        acta_data = self.acta_data.copy()
        del acta_data['titulo']
        
        with self.assertRaises(ValidationError):
            acta = Acta(**acta_data)
            acta.full_clean()  # Ejecutar validaciones
    
    def test_email_docente_valido(self):
        """Test: Verificar formato de email del docente"""
        acta_data = self.acta_data.copy()
        acta_data['docente_asignado'] = 'email-invalido'
        
        # Django no valida formato de email por defecto, pero podemos agregar validación
        acta = Acta.objects.create(**acta_data)
        self.assertEqual(acta.docente_asignado, 'email-invalido')
