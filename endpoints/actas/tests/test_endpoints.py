from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import json
import uuid
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Acta
from model.File import File, Doctype, LifeCycleState, Team
from ucasal.utils import ActaStates

class ActasEndpointsTest(TestCase):
    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear datos de prueba necesarios para File
        # Usar valores de ActaStates que coincidan con los que esperan los endpoints
        self.team = Team.objects.create(name='test_team', label='Test Team')
        self.doctype = Doctype.objects.create(name='acta', label='Acta')
        self.lifecycle_state = LifeCycleState.objects.create(name=ActaStates.pendiente_otp)
        
        # Crear acta de prueba
        acta_uuid = uuid.uuid4()
        self.acta = Acta.objects.create(
            uuid=acta_uuid,
            titulo='Acta de Prueba',
            descripcion='Descripción de prueba',
            docente_asignado='profesor@ucasal.edu.ar',
            nombre_docente='Dr. Test',
            codigo_sector='001',
            estado='pendiente_otp'
        )
        
        # Crear File correspondiente (los endpoints usan File, no Acta)
        # Crear un archivo temporal para el File
        test_file = SimpleUploadedFile(
            "test_acta.pdf",
            b"fake pdf content",
            content_type="application/pdf"
        )
        
        # Asignar valores directamente a los campos para evitar problemas con setters durante creación
        self.file = File(
            uuid=acta_uuid,
            titulo='Acta de Prueba',
            doctype_obj=self.doctype,
            life_cycle_state_obj=self.lifecycle_state,
            estado='pendiente_otp',
            file=test_file
        )
        # Asignar valores legacy directamente (db_column='doctype' y 'life_cycle_state')
        # Estos campos se mapean a las columnas correctas en la BD después de la migración 0002
        self.file.doctype_legacy = 'acta'
        self.file.life_cycle_state_legacy = ActaStates.pendiente_otp
        self.file.save()
        # Agregar metadata necesaria para los endpoints
        self.file.set_metadata('metadata.acta_docente_asignado', 'profesor@ucasal.edu.ar')
        self.file.set_metadata('metadata.acta_nombre_docente_asignado', 'Dr. Test')
    
    def test_home_endpoint(self):
        """Test: Endpoint principal"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('endpoints', data)
        self.assertIn('UCASAL API', data['message'])
    
    def test_docs_endpoint(self):
        """Test: Endpoint de documentación"""
        response = self.client.get('/docs/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('title', data)
        self.assertIn('endpoints', data)
        self.assertEqual(data['title'], 'UCASAL API Documentation')
    
    def test_getconfig_endpoint_success(self):
        """Test: Endpoint getconfig exitoso"""
        data = {
            'key': 'test_key',
            'is_secret': False
        }
        
        response = self.client.post('/actas/getconfig/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('mocked_value_for_test_key', response.content.decode())
    
    def test_getconfig_endpoint_missing_key(self):
        """Test: Endpoint getconfig sin key"""
        data = {
            'is_secret': False
        }
        
        response = self.client.post('/actas/getconfig/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 500)  # Error por key faltante
    
    def test_qr_endpoint_success(self):
        """Test: Endpoint QR exitoso"""
        data = {
            'url': 'https://example.com'
        }
        
        response = self.client.post('/actas/qr/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(len(response.content) > 0)
    
    def test_qr_endpoint_missing_url(self):
        """Test: Endpoint QR sin URL"""
        data = {}
        
        response = self.client.post('/actas/qr/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)  # Usa URL por defecto
    
    def test_qr_endpoint_wrong_method(self):
        """Test: Endpoint QR con método incorrecto"""
        response = self.client.get('/actas/qr/')
        self.assertEqual(response.status_code, 405)  # Method not allowed
    
    def test_registerotp_endpoint_acta_not_found(self):
        """Test: Endpoint registerotp con acta inexistente"""
        fake_uuid = uuid.uuid4()
        data = {
            'otp': '123456',
            'ip': '192.168.1.1',
            'latitude': -34.6037,
            'longitude': -58.3816,
            'accuracy': '10m',
            'user_agent': 'Mozilla/5.0'
        }
        
        response = self.client.post(f'/actas/{fake_uuid}/registerotp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.validate_otp')
    def test_registerotp_endpoint_invalid_otp(self, mock_validate_otp):
        """Test: Endpoint registerotp con OTP inválido"""
        from model.exceptions.invalid_otp_error import InvalidOtpError
        # Mockear para que lance InvalidOtpError
        mock_validate_otp.side_effect = InvalidOtpError('OTP inválido')
        
        data = {
            'otp': '123456',
            'ip': '192.168.1.1',
            'latitude': -34.6037,
            'longitude': -58.3816,
            'accuracy': '10m',
            'user_agent': 'Mozilla/5.0'
        }
        
        response = self.client.post(f'/actas/{self.file.uuid}/registerotp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        mock_validate_otp.assert_called_once()
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.validate_otp')
    @patch('external_services.ucasal.ucasal_services.UcasalServices.get_auth_token')
    def test_registerotp_endpoint_missing_fields(self, mock_get_token, mock_validate_otp):
        """Test: Endpoint registerotp con campos faltantes"""
        # Mockear servicios para que pasen la validación de OTP
        mock_validate_otp.return_value = None  # No lanza excepción
        mock_get_token.return_value = 'mock_token'
        
        data = {
            'otp': '123456'
            # Faltan otros campos requeridos: ip, latitude, longitude, accuracy, user_agent
        }
        
        response = self.client.post(f'/actas/{self.file.uuid}/registerotp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        # El endpoint debería validar los campos faltantes y retornar 400
        self.assertEqual(response.status_code, 400)
    
    def test_sendotp_endpoint_success(self):
        """Test: Endpoint sendotp exitoso"""
        response = self.client.post(f'/actas/{self.file.uuid}/sendotp/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('sent_to', data)
        self.assertIn('expiration', data)
    
    def test_sendotp_endpoint_wrong_method(self):
        """Test: Endpoint sendotp con método incorrecto"""
        response = self.client.get(f'/actas/{self.file.uuid}/sendotp/')
        self.assertEqual(response.status_code, 405)
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.get_auth_token')
    @patch('external_services.ucasal.ucasal_services.UcasalServices.notify_blockchain_success')
    def test_bfaresponse_endpoint_success(self, mock_notify, mock_get_token):
        """Test: Endpoint bfaresponse exitoso"""
        # Mockear servicios externos
        mock_get_token.return_value = 'mock_auth_token'
        mock_notify.return_value = 'mock_response'
        
        # Cambiar estado a pendiente_blockchain en File (los endpoints usan File)
        # Usar el valor exacto de ActaStates
        blockchain_state = LifeCycleState.objects.create(name=ActaStates.pendiente_blockchain)
        self.file.life_cycle_state_obj = blockchain_state
        self.file.life_cycle_state_legacy = ActaStates.pendiente_blockchain
        self.file.save()
        
        data = {
            'status': 'success'
        }
        
        response = self.client.post(f'/actas/{self.file.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que los servicios fueron llamados
        mock_get_token.assert_called_once()
        mock_notify.assert_called_once()
    
    def test_bfaresponse_endpoint_invalid_status(self):
        """Test: Endpoint bfaresponse con status inválido"""
        data = {
            'status': 'invalid_status'
        }
        
        response = self.client.post(f'/actas/{self.file.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.get_auth_token')
    @patch('external_services.ucasal.ucasal_services.UcasalServices.notify_rejection')
    def test_reject_endpoint_success(self, mock_notify, mock_get_token):
        """Test: Endpoint reject exitoso"""
        # Mockear servicios externos
        mock_get_token.return_value = 'mock_auth_token'
        mock_notify.return_value = 'mock_response'
        
        # Asegurar que el File está en estado pendiente_otp
        self.file.life_cycle_state_obj = self.lifecycle_state
        self.file.life_cycle_state_legacy = ActaStates.pendiente_otp
        self.file.save()
        
        data = {
            'motivo': 'Error en los datos'
        }
        
        response = self.client.post(f'/actas/{self.file.uuid}/reject/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que los servicios fueron llamados
        mock_get_token.assert_called_once()
        mock_notify.assert_called_once()
    
    def test_reject_endpoint_missing_motivo(self):
        """Test: Endpoint reject sin motivo"""
        data = {}
        
        response = self.client.post(f'/actas/{self.file.uuid}/reject/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_reject_endpoint_wrong_state(self):
        """Test: Endpoint reject con estado incorrecto"""
        # Cambiar a estado que no permite rechazo en File
        firmada_state = LifeCycleState.objects.create(name=ActaStates.firmada)
        self.file.life_cycle_state_obj = firmada_state
        self.file.life_cycle_state_legacy = ActaStates.firmada
        self.file.save()
        
        data = {
            'motivo': 'Error en los datos'
        }
        
        response = self.client.post(f'/actas/{self.file.uuid}/reject/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_endpoints_require_post(self):
        """Test: Verificar que endpoints requieren POST"""
        endpoints = [
            '/actas/qr/',
            '/actas/getconfig/',
            f'/actas/{self.file.uuid}/registerotp/',
            f'/actas/{self.file.uuid}/sendotp/',
            f'/actas/{self.file.uuid}/bfaresponse/',
            f'/actas/{self.file.uuid}/reject/'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 405)
    
    def test_cors_headers(self):
        """Test: Verificar headers CORS"""
        response = self.client.get('/')
        self.assertIn('X-Frame-Options', response)
        self.assertIn('X-Content-Type-Options', response)

