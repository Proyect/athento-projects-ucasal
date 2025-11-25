from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import json
import uuid
from unittest.mock import patch, MagicMock, Mock
from django.core.files.uploadedfile import SimpleUploadedFile
from model.File import File, Doctype, LifeCycleState, Team, Serie
from ucasal.utils import TituloStates, titulo_doctype_name


class TitulosEndpointsTest(TestCase):
    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear datos de prueba necesarios para File
        self.team = Team.objects.create(name='test_team', label='Test Team')
        self.doctype = Doctype.objects.create(name=titulo_doctype_name, label='Títulos')
        self.serie = Serie.objects.create(name='títulos', label='Títulos', team=self.team)
        self.lifecycle_state = LifeCycleState.objects.create(name=TituloStates.recibido)
        
        # Crear título de prueba
        titulo_uuid = uuid.uuid4()
        self.titulo_file = File(
            uuid=titulo_uuid,
            titulo='Título de Prueba',
            doctype_obj=self.doctype,
            life_cycle_state_obj=self.lifecycle_state,
            serie=self.serie,
            estado=TituloStates.recibido,
            doctype_legacy=titulo_doctype_name,
            life_cycle_state_legacy=TituloStates.recibido
        )
        self.titulo_file.save()
        
        # Agregar metadata necesaria para los endpoints
        self.titulo_file.set_metadata('metadata.titulo_dni', '8205853')
        self.titulo_file.set_metadata('metadata.titulo_tipo_dni', 'DNI')
        self.titulo_file.set_metadata('metadata.titulo_lugar', '10')
    
    def test_qr_endpoint_success(self):
        """Test: Endpoint QR para títulos exitoso"""
        data = {
            'url': 'https://www.ucasal.edu.ar/validar/titulo/test-uuid'
        }
        
        response = self.client.post('/titulos/qr/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(len(response.content) > 0)
    
    def test_qr_endpoint_missing_url(self):
        """Test: Endpoint QR sin URL"""
        data = {}
        
        response = self.client.post('/titulos/qr/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)  # Usa URL por defecto
        self.assertEqual(response['Content-Type'], 'image/png')
    
    def test_qr_endpoint_wrong_method(self):
        """Test: Endpoint QR con método incorrecto"""
        response = self.client.get('/titulos/qr/')
        self.assertEqual(response.status_code, 405)  # Method not allowed
    
    @patch('endpoints.titulos.titulos.requests.post')
    @patch('ucasal.mocks.sp_athento_config.SpAthentoConfig')
    def test_recibir_titulo_endpoint_success(self, mock_sac_class, mock_requests):
        """Test: Endpoint recibir_titulo exitoso"""
        # Mockear configuración de Athento
        mock_sac_instance = MagicMock()
        mock_sac_instance.get_str.side_effect = lambda key, default=None, is_secret=False: {
            'athento.base_url': 'https://ucasal-uat.athento.com',
            'athento.api.user': 'test@athento.com',
            'athento.api.password': 'test_password'
        }.get(key, default)
        mock_sac_class.return_value = mock_sac_instance
        
        # Mockear respuesta de Athento
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'test-uuid-123',
            'uuid': 'test-uuid-123'
        }
        mock_response.text = '{"id": "test-uuid-123"}'
        mock_requests.return_value = mock_response
        
        # Crear PDF de prueba
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF'
        pdf_file = SimpleUploadedFile(
            "titulo_test.pdf",
            pdf_content,
            content_type="application/pdf"
        )
        
        # Datos del form-data
        data = {
            'filename': '8205853/10/3/16/2/8707',
            'serie': 'títulos',
            'doctype': 'títulos',
            'json_data': json.dumps({
                'DNI': '8205853',
                'Tipo DNI': 'DNI',
                'Lugar': '10',
                'Facultad': '3',
                'Carrera': '16',
                'Modalidad': '2',
                'Plan': '8707',
                'Título': 'Abogado'
            }),
            'file': pdf_file
        }
        
        # Mockear el import dentro de la función
        with patch('endpoints.titulos.titulos.SpAthentoConfig', mock_sac_instance):
            response = self.client.post('/titulos/recibir/', 
                                      data=data,
                                      format='multipart')
        
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get('success'))
        self.assertIn('uuid', response_data)
    
    def test_recibir_titulo_endpoint_missing_filename(self):
        """Test: Endpoint recibir_titulo sin filename"""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF'
        pdf_file = SimpleUploadedFile(
            "titulo_test.pdf",
            pdf_content,
            content_type="application/pdf"
        )
        
        data = {
            'file': pdf_file,
            'serie': 'títulos',
            'doctype': 'títulos'
        }
        
        response = self.client.post('/titulos/recibir/', 
                                  data=data,
                                  format='multipart')
        
        self.assertEqual(response.status_code, 400)
    
    def test_recibir_titulo_endpoint_missing_file(self):
        """Test: Endpoint recibir_titulo sin archivo"""
        data = {
            'filename': '8205853/10/3/16/2/8707',
            'serie': 'títulos',
            'doctype': 'títulos'
        }
        
        response = self.client.post('/titulos/recibir/', 
                                  data=data,
                                  format='multipart')
        
        self.assertEqual(response.status_code, 400)
    
    def test_recibir_titulo_endpoint_invalid_filename_format(self):
        """Test: Endpoint recibir_titulo con formato de filename inválido"""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF'
        pdf_file = SimpleUploadedFile(
            "titulo_test.pdf",
            pdf_content,
            content_type="application/pdf"
        )
        
        data = {
            'filename': '8205853/10/3',  # Formato incorrecto
            'file': pdf_file,
            'serie': 'títulos',
            'doctype': 'títulos'
        }
        
        response = self.client.post('/titulos/recibir/', 
                                  data=data,
                                  format='multipart')
        
        self.assertEqual(response.status_code, 400)
    
    def test_recibir_titulo_endpoint_invalid_file_type(self):
        """Test: Endpoint recibir_titulo con archivo que no es PDF"""
        text_content = b'This is not a PDF'
        text_file = SimpleUploadedFile(
            "test.txt",
            text_content,
            content_type="text/plain"
        )
        
        data = {
            'filename': '8205853/10/3/16/2/8707',
            'file': text_file,
            'serie': 'títulos',
            'doctype': 'títulos'
        }
        
        response = self.client.post('/titulos/recibir/', 
                                  data=data,
                                  format='multipart')
        
        self.assertEqual(response.status_code, 400)
    
    def test_recibir_titulo_endpoint_wrong_method(self):
        """Test: Endpoint recibir_titulo con método incorrecto"""
        response = self.client.get('/titulos/recibir/')
        self.assertEqual(response.status_code, 405)
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.get_auth_token')
    @patch('endpoints.titulos.titulos.requests.patch')
    def test_informar_estado_endpoint_success(self, mock_patch, mock_get_token):
        """Test: Endpoint informar_estado exitoso"""
        # Mockear servicios externos
        mock_get_token.return_value = 'mock_auth_token'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response
        
        data = {
            'estado': TituloStates.aprobado_ua,
            'observaciones': 'Título aprobado correctamente'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/estado/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get('success'))
        self.assertEqual(response_data.get('estado'), TituloStates.aprobado_ua)
        mock_get_token.assert_called_once()
        mock_patch.assert_called_once()
    
    def test_informar_estado_endpoint_titulo_not_found(self):
        """Test: Endpoint informar_estado con título inexistente"""
        fake_uuid = uuid.uuid4()
        data = {
            'estado': TituloStates.aprobado_ua
        }
        
        response = self.client.post(f'/titulos/{fake_uuid}/estado/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
    
    def test_informar_estado_endpoint_missing_estado(self):
        """Test: Endpoint informar_estado sin estado"""
        data = {}
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/estado/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_informar_estado_endpoint_wrong_method(self):
        """Test: Endpoint informar_estado con método incorrecto"""
        response = self.client.get(f'/titulos/{self.titulo_file.uuid}/estado/')
        self.assertEqual(response.status_code, 405)
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.validate_otp')
    def test_validar_otp_endpoint_success(self, mock_validate):
        """Test: Endpoint validar_otp exitoso"""
        # Mockear validación de OTP
        mock_validate.return_value = None  # No lanza excepción = válido
        
        data = {
            'otp': '123456',
            'usuario': 'test@ucasal.edu.ar'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/validar-otp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get('otp_valido'))
        self.assertEqual(response_data.get('usuario'), 'test@ucasal.edu.ar')
        mock_validate.assert_called_once_with(user='test@ucasal.edu.ar', otp=123456)
    
    def test_validar_otp_endpoint_titulo_not_found(self):
        """Test: Endpoint validar_otp con título inexistente"""
        fake_uuid = uuid.uuid4()
        data = {
            'otp': '123456',
            'usuario': 'test@ucasal.edu.ar'
        }
        
        response = self.client.post(f'/titulos/{fake_uuid}/validar-otp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
    
    def test_validar_otp_endpoint_missing_usuario(self):
        """Test: Endpoint validar_otp sin usuario"""
        data = {
            'otp': '123456'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/validar-otp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_validar_otp_endpoint_invalid_otp(self):
        """Test: Endpoint validar_otp con OTP inválido"""
        data = {
            'otp': 'invalid_otp',
            'usuario': 'test@ucasal.edu.ar'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/validar-otp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.validate_otp')
    def test_validar_otp_endpoint_invalid_otp_from_service(self, mock_validate):
        """Test: Endpoint validar_otp con OTP rechazado por servicio"""
        from model.exceptions.invalid_otp_error import InvalidOtpError
        
        # Mockear rechazo de OTP
        mock_validate.side_effect = InvalidOtpError('El código OTP es inválido o ha expirado.')
        
        data = {
            'otp': '123456',
            'usuario': 'test@ucasal.edu.ar'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/validar-otp/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_validar_otp_endpoint_wrong_method(self):
        """Test: Endpoint validar_otp con método incorrecto"""
        response = self.client.get(f'/titulos/{self.titulo_file.uuid}/validar-otp/')
        self.assertEqual(response.status_code, 405)
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.get_auth_token')
    @patch('external_services.ucasal.ucasal_services.UcasalServices.notify_blockchain_success')
    def test_bfaresponse_endpoint_success(self, mock_notify, mock_get_token):
        """Test: Endpoint bfaresponse exitoso"""
        # Mockear servicios externos
        mock_get_token.return_value = 'mock_auth_token'
        mock_notify.return_value = 'mock_response'
        
        # Cambiar estado a pendiente_blockchain
        blockchain_state = LifeCycleState.objects.create(name=TituloStates.pendiente_blockchain)
        self.titulo_file.life_cycle_state_obj = blockchain_state
        self.titulo_file.life_cycle_state_legacy = TituloStates.pendiente_blockchain
        self.titulo_file.save()
        
        data = {
            'status': 'success'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que los servicios fueron llamados
        mock_get_token.assert_called_once()
        mock_notify.assert_called_once()
    
    @patch('external_services.ucasal.ucasal_services.UcasalServices.get_auth_token')
    @patch('external_services.ucasal.ucasal_services.UcasalServices.notify_blockchain_success')
    def test_bfaresponse_endpoint_failure(self, mock_notify, mock_get_token):
        """Test: Endpoint bfaresponse con status failure"""
        # Mockear servicios externos
        mock_get_token.return_value = 'mock_auth_token'
        mock_notify.return_value = 'mock_response'
        
        # Cambiar estado a pendiente_blockchain
        blockchain_state = LifeCycleState.objects.create(name=TituloStates.pendiente_blockchain)
        self.titulo_file.life_cycle_state_obj = blockchain_state
        self.titulo_file.life_cycle_state_legacy = TituloStates.pendiente_blockchain
        self.titulo_file.save()
        
        data = {
            'status': 'failure'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        # Con failure no se debe llamar a notify_blockchain_success
        mock_notify.assert_not_called()
    
    def test_bfaresponse_endpoint_invalid_status(self):
        """Test: Endpoint bfaresponse con status inválido"""
        data = {
            'status': 'invalid_status'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_bfaresponse_endpoint_titulo_not_found(self):
        """Test: Endpoint bfaresponse con título inexistente"""
        fake_uuid = uuid.uuid4()
        data = {
            'status': 'success'
        }
        
        response = self.client.post(f'/titulos/{fake_uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
    
    def test_bfaresponse_endpoint_invalid_state(self):
        """Test: Endpoint bfaresponse con estado inválido"""
        # El título está en estado recibido, no puede recibir callback de blockchain
        data = {
            'status': 'success'
        }
        
        response = self.client.post(f'/titulos/{self.titulo_file.uuid}/bfaresponse/', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_bfaresponse_endpoint_wrong_method(self):
        """Test: Endpoint bfaresponse con método incorrecto"""
        response = self.client.get(f'/titulos/{self.titulo_file.uuid}/bfaresponse/')
        self.assertEqual(response.status_code, 405)

