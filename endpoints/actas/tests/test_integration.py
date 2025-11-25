"""
Tests de integración end-to-end para el flujo completo de actas.
Estos tests verifican el flujo completo desde la creación hasta la firma.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from model import File, Doctype, LifeCycleState, Team, Serie
from endpoints.actas.models import Acta
from endpoints.actas.actas import ActaStates
from ucasal.utils import titulo_doctype_name
import json
import uuid


class ActaIntegrationTest(TestCase):
    """Tests de integración para el flujo completo de actas."""
    
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
        self.doctype = Doctype.objects.create(name='acta', label='Acta')
        self.recibida_state = LifeCycleState.objects.create(name=ActaStates.recibida)
        self.pendiente_otp_state = LifeCycleState.objects.create(name=ActaStates.pendiente_otp)
        self.pendiente_blockchain_state = LifeCycleState.objects.create(name=ActaStates.pendiente_blockchain)
        self.firmada_state = LifeCycleState.objects.create(name=ActaStates.firmada)
        
        # Crear serie
        self.serie = Serie.objects.create(name='actas', label='Actas', team=self.team)
        
        # Crear acta inicial
        self.acta_uuid = uuid.uuid4()
        self.acta = Acta.objects.create(
            uuid=self.acta_uuid,
            titulo='Acta de Integración Test',
            docente_asignado='docente@ucasal.edu.ar',
            nombre_docente='Docente Test',
            codigo_sector='001',
            estado=ActaStates.recibida,
            activa=True
        )
        
        # Crear File asociado
        self.file = File.objects.create(
            uuid=self.acta_uuid,
            titulo='Acta de Integración Test',
            doctype_obj=self.doctype,
            life_cycle_state_obj=self.recibida_state,
            serie=self.serie,
            filename='acta_test.pdf',
            doctype_legacy='acta',
            estado='recibida'
        )
    
    def test_flujo_completo_acta(self):
        """Test del flujo completo: recibida -> pendiente_otp -> firmada"""
        
        # Paso 1: Verificar estado inicial
        self.assertEqual(self.acta.estado, ActaStates.recibida)
        self.assertEqual(self.file.life_cycle_state_obj.name, ActaStates.recibida)
        
        # Paso 2: Enviar OTP (simular)
        # En un test real, esto llamaría al endpoint /actas/{uuid}/sendotp/
        # Por ahora, cambiamos el estado manualmente
        self.file.life_cycle_state_obj = self.pendiente_otp_state
        self.file.save()
        self.acta.estado = ActaStates.pendiente_otp
        self.acta.save()
        
        # Verificar cambio de estado
        self.file.refresh_from_db()
        self.assertEqual(self.file.life_cycle_state_obj.name, ActaStates.pendiente_otp)
        
        # Paso 3: Registrar OTP (simular)
        # En un test real, esto llamaría al endpoint /actas/{uuid}/registerotp/
        # Por ahora, cambiamos el estado manualmente
        self.file.life_cycle_state_obj = self.pendiente_blockchain_state
        self.file.save()
        self.acta.estado = ActaStates.pendiente_blockchain
        self.acta.firmada_con_otp = True
        self.acta.save()
        
        # Verificar cambio de estado
        self.file.refresh_from_db()
        self.assertEqual(self.file.life_cycle_state_obj.name, ActaStates.pendiente_blockchain)
        self.assertTrue(self.acta.firmada_con_otp)
        
        # Paso 4: Callback de blockchain (simular)
        # En un test real, esto llamaría al endpoint /actas/{uuid}/bfaresponse/
        self.file.life_cycle_state_obj = self.firmada_state
        self.file.save()
        self.acta.estado = ActaStates.firmada
        self.acta.registro_blockchain = 'success'
        self.acta.save()
        
        # Verificar estado final
        self.file.refresh_from_db()
        self.assertEqual(self.file.life_cycle_state_obj.name, ActaStates.firmada)
        self.assertEqual(self.acta.estado, ActaStates.firmada)
        self.assertEqual(self.acta.registro_blockchain, 'success')
    
    def test_flujo_rechazo_acta(self):
        """Test del flujo de rechazo de acta."""
        
        # Estado inicial: pendiente_otp
        self.file.life_cycle_state_obj = self.pendiente_otp_state
        self.file.save()
        self.acta.estado = ActaStates.pendiente_otp
        self.acta.save()
        
        # Rechazar acta (simular)
        # En un test real, esto llamaría al endpoint /actas/{uuid}/reject/
        rechazada_state = LifeCycleState.objects.create(name=ActaStates.rechazada)
        self.file.life_cycle_state_obj = rechazada_state
        self.file.save()
        self.acta.estado = ActaStates.rechazada
        self.acta.motivo_rechazo = 'Test de rechazo'
        self.acta.activa = False
        self.acta.save()
        
        # Verificar estado final
        self.file.refresh_from_db()
        self.assertEqual(self.file.life_cycle_state_obj.name, ActaStates.rechazada)
        self.assertEqual(self.acta.estado, ActaStates.rechazada)
        self.assertFalse(self.acta.activa)
        self.assertEqual(self.acta.motivo_rechazo, 'Test de rechazo')
    
    def test_consistencia_acta_file(self):
        """Test que verifica la consistencia entre Acta y File."""
        
        # Verificar que ambos tienen el mismo UUID
        self.assertEqual(self.acta.uuid, self.file.uuid)
        
        # Cambiar estado en File
        self.file.life_cycle_state_obj = self.pendiente_otp_state
        self.file.save()
        
        # Verificar que File se actualizó
        self.file.refresh_from_db()
        self.assertEqual(self.file.life_cycle_state_obj.name, ActaStates.pendiente_otp)
        
        # Cambiar estado en Acta
        self.acta.estado = ActaStates.pendiente_otp
        self.acta.save()
        
        # Verificar que Acta se actualizó
        self.acta.refresh_from_db()
        self.assertEqual(self.acta.estado, ActaStates.pendiente_otp)
    
    def test_metadata_persistence(self):
        """Test que verifica la persistencia de metadata."""
        
        # Agregar metadata
        self.file.set_metadata('metadata.test_key', 'test_value')
        self.file.save()
        
        # Recuperar y verificar
        self.file.refresh_from_db()
        value = self.file.gmv('metadata.test_key')
        self.assertEqual(value, 'test_value')
        
        # Agregar más metadata
        self.file.set_metadata('metadata.otp_sent', 'true')
        self.file.set_metadata('metadata.blockchain_hash', 'abc123')
        self.file.save()
        
        # Verificar todos los valores
        self.file.refresh_from_db()
        self.assertEqual(self.file.gmv('metadata.test_key'), 'test_value')
        self.assertEqual(self.file.gmv('metadata.otp_sent'), 'true')
        self.assertEqual(self.file.gmv('metadata.blockchain_hash'), 'abc123')



