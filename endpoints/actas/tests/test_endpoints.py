from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import json
import uuid
from ..models import Acta

class ActasEndpointsTest(TestCase):
    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear acta de prueba
        self.acta = Acta.objects.create(
            uuid=uuid.uuid4(),
            titulo='Acta de Prueba',
            descripcion='Descripción de prueba',
            docente_asignado='profesor@ucasal.edu.ar',
            nombre_docente='Dr. Test',
            codigo_sector='001',
            estado='pendiente_otp'
        )
    
    def test_home_endpoint(self):
        """Test: Endpoint principal"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('endpoints', data)
        self.assertEqual(data['message'], 'UCASAL API - Sistema de Actas')
    
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
    
    def test_registerotp_endpoint_invalid_otp(self):
        """Test: Endpoint registerotp con OTP inválido"""
        data = {
            'otp': 'invalid_otp',
            'ip': '192.168.1.1',
            'latitude': -34.6037,
            'longitude': -58.3816,
            'accuracy': '10m',
            'user_agent': 'Mozilla/5.0'
        }
        
        response = self.client.post(f'/actas/{self.acta.uuid}/registerotp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_registerotp_endpoint_missing_fields(self):
        """Test: Endpoint registerotp con campos faltantes"""
        data = {
            'otp': '123456'
            # Faltan otros campos requeridos
        }
        
        response = self.client.post(f'/actas/{self.acta.uuid}/registerotp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_sendotp_endpoint_success(self):
        """Test: Endpoint sendotp exitoso"""
        response = self.client.post(f'/actas/{self.acta.uuid}/sendotp/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('sent_to', data)
        self.assertIn('expiration', data)
    
    def test_sendotp_endpoint_wrong_method(self):
        """Test: Endpoint sendotp con método incorrecto"""
        response = self.client.get(f'/actas/{self.acta.uuid}/sendotp/')
        self.assertEqual(response.status_code, 405)
    
    def test_bfaresponse_endpoint_success(self):
        """Test: Endpoint bfaresponse exitoso"""
        # Cambiar estado a pendiente_blockchain
        self.acta.estado = 'pendiente_blockchain'
        self.acta.save()
        
        data = {
            'status': 'success'
        }
        
        response = self.client.post(f'/actas/{self.acta.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
    
    def test_bfaresponse_endpoint_invalid_status(self):
        """Test: Endpoint bfaresponse con status inválido"""
        data = {
            'status': 'invalid_status'
        }
        
        response = self.client.post(f'/actas/{self.acta.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_reject_endpoint_success(self):
        """Test: Endpoint reject exitoso"""
        data = {
            'motivo': 'Error en los datos'
        }
        
        response = self.client.post(f'/actas/{self.acta.uuid}/reject/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
    
    def test_reject_endpoint_missing_motivo(self):
        """Test: Endpoint reject sin motivo"""
        data = {}
        
        response = self.client.post(f'/actas/{self.acta.uuid}/reject/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_reject_endpoint_wrong_state(self):
        """Test: Endpoint reject con estado incorrecto"""
        # Cambiar a estado que no permite rechazo
        self.acta.estado = 'firmada'
        self.acta.save()
        
        data = {
            'motivo': 'Error en los datos'
        }
        
        response = self.client.post(f'/actas/{self.acta.uuid}/reject/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_endpoints_require_post(self):
        """Test: Verificar que endpoints requieren POST"""
        endpoints = [
            '/actas/qr/',
            '/actas/getconfig/',
            f'/actas/{self.acta.uuid}/registerotp/',
            f'/actas/{self.acta.uuid}/sendotp/',
            f'/actas/{self.acta.uuid}/bfaresponse/',
            f'/actas/{self.acta.uuid}/reject/'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 405)
    
    def test_cors_headers(self):
        """Test: Verificar headers CORS"""
        response = self.client.get('/')
        self.assertIn('X-Frame-Options', response)
        self.assertIn('X-Content-Type-Options', response)

