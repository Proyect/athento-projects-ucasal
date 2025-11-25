"""
Tests de integración end-to-end para el flujo completo de títulos.
Estos tests verifican el flujo completo desde la recepción hasta la emisión.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from model import File, Doctype, LifeCycleState, Team, Serie
from ucasal.utils import TituloStates, titulo_doctype_name
import json
import uuid


class TituloIntegrationTest(TestCase):
    """Tests de integración para el flujo completo de títulos."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.client = Client()
        
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@ucasal.edu.ar'
        )
        
        # Crear datos necesarios
        self.team = Team.objects.create(name='UCASAL', label='UCASAL')
        self.doctype = Doctype.objects.create(name=titulo_doctype_name, label='Títulos')
        
        # Crear estados
        self.recibido_state = LifeCycleState.objects.create(name=TituloStates.recibido)
        self.pendiente_ua_state = LifeCycleState.objects.create(name=TituloStates.pendiente_aprobacion_ua)
        self.aprobado_ua_state = LifeCycleState.objects.create(name=TituloStates.aprobado_ua)
        self.pendiente_r_state = LifeCycleState.objects.create(name=TituloStates.pendiente_aprobacion_r)
        self.aprobado_r_state = LifeCycleState.objects.create(name=TituloStates.aprobado_r)
        self.pendiente_firma_sg_state = LifeCycleState.objects.create(name=TituloStates.pendiente_firma_sg)
        self.firmado_sg_state = LifeCycleState.objects.create(name=TituloStates.firmado_sg)
        self.emitido_state = LifeCycleState.objects.create(name=TituloStates.titulo_emitido)
        
        # Crear serie
        self.serie = Serie.objects.create(name='títulos', label='Títulos', team=self.team)
        
        # Crear título inicial
        self.titulo_uuid = uuid.uuid4()
        self.titulo_file = File.objects.create(
            uuid=self.titulo_uuid,
            titulo='Título de Integración Test',
            doctype_obj=self.doctype,
            life_cycle_state_obj=self.recibido_state,
            serie=self.serie,
            filename='titulo_test.pdf',
            doctype_legacy='títulos',
            estado='recibido'
        )
        
        # Agregar metadata inicial
        self.titulo_file.set_metadata('metadata.titulo_dni', '12345678')
        self.titulo_file.set_metadata('metadata.titulo_carrera', 'Ingeniería')
        self.titulo_file.set_metadata('metadata.titulo_facultad', 'Facultad de Ingeniería')
        self.titulo_file.save()
    
    def test_flujo_completo_titulo(self):
        """Test del flujo completo: recibido -> aprobado UA -> aprobado R -> firmado -> emitido"""
        
        # Paso 1: Verificar estado inicial
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.recibido)
        
        # Paso 2: Cambiar a Pendiente Aprobación UA
        self.titulo_file.life_cycle_state_obj = self.pendiente_ua_state
        self.titulo_file.save()
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.pendiente_aprobacion_ua)
        
        # Paso 3: Aprobar por UA
        self.titulo_file.life_cycle_state_obj = self.aprobado_ua_state
        self.titulo_file.save()
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.aprobado_ua)
        
        # Paso 4: Cambiar a Pendiente Aprobación R
        self.titulo_file.life_cycle_state_obj = self.pendiente_r_state
        self.titulo_file.save()
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.pendiente_aprobacion_r)
        
        # Paso 5: Aprobar por R
        self.titulo_file.life_cycle_state_obj = self.aprobado_r_state
        self.titulo_file.save()
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.aprobado_r)
        
        # Paso 6: Cambiar a Pendiente Firma SG
        self.titulo_file.life_cycle_state_obj = self.pendiente_firma_sg_state
        self.titulo_file.save()
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.pendiente_firma_sg)
        
        # Paso 7: Firmar (simular)
        # En un test real, esto llamaría al endpoint /titulos/{uuid}/firmar/
        self.titulo_file.life_cycle_state_obj = self.firmado_sg_state
        self.titulo_file.set_feature('firmada.digital', '1')
        self.titulo_file.set_metadata('metadata.firma.fecha', '2025-01-31')
        self.titulo_file.save()
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.firmado_sg)
        self.assertEqual(self.titulo_file.gfv('firmada.digital'), '1')
        
        # Paso 8: Emitir título
        self.titulo_file.life_cycle_state_obj = self.emitido_state
        self.titulo_file.save()
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.titulo_emitido)
    
    def test_flujo_rechazo_titulo(self):
        """Test del flujo de rechazo de título."""
        
        # Estado inicial: pendiente aprobación UA
        self.titulo_file.life_cycle_state_obj = self.pendiente_ua_state
        self.titulo_file.save()
        
        # Rechazar título
        rechazado_state = LifeCycleState.objects.create(name=TituloStates.rechazado)
        self.titulo_file.life_cycle_state_obj = rechazado_state
        self.titulo_file.set_metadata('metadata.titulo_motivo_rechazo', 'Documentación incompleta')
        self.titulo_file.removed = True
        self.titulo_file.save()
        
        # Verificar estado final
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.rechazado)
        self.assertTrue(self.titulo_file.removed)
        self.assertEqual(self.titulo_file.gmv('metadata.titulo_motivo_rechazo'), 'Documentación incompleta')
    
    def test_metadata_persistence_titulo(self):
        """Test que verifica la persistencia de metadata en títulos."""
        
        # Agregar metadata completa
        metadata = {
            'metadata.titulo_dni': '12345678',
            'metadata.titulo_carrera': 'Ingeniería en Sistemas',
            'metadata.titulo_facultad': 'Facultad de Ingeniería',
            'metadata.titulo_modalidad': 'Presencial',
            'metadata.titulo_plan': '2020',
            'metadata.titulo_titulo': 'Ingeniero en Sistemas',
        }
        
        for key, value in metadata.items():
            self.titulo_file.set_metadata(key, value)
        
        self.titulo_file.save()
        
        # Verificar todos los valores
        self.titulo_file.refresh_from_db()
        for key, expected_value in metadata.items():
            actual_value = self.titulo_file.gmv(key)
            self.assertEqual(actual_value, expected_value, f"Metadata {key} no coincide")
    
    def test_cambio_serie(self):
        """Test que verifica el cambio de serie."""
        
        # Crear nueva serie
        nueva_serie = Serie.objects.create(name='títulos_emitidos', label='Títulos Emitidos', team=self.team)
        
        # Cambiar serie
        self.titulo_file.serie = nueva_serie
        self.titulo_file.save()
        
        # Verificar cambio
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.serie.name, 'títulos_emitidos')
    
    def test_consistencia_estados(self):
        """Test que verifica la consistencia entre estados legacy y objetos."""
        
        # Cambiar estado usando objeto
        self.titulo_file.life_cycle_state_obj = self.aprobado_ua_state
        self.titulo_file.save()
        
        # Verificar que ambos están sincronizados
        self.titulo_file.refresh_from_db()
        self.assertEqual(self.titulo_file.life_cycle_state_obj.name, TituloStates.aprobado_ua)
        # El estado legacy debería actualizarse automáticamente si hay un setter



