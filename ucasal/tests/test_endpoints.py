from django.test import TestCase, Client
from django.urls import reverse

class ActasEndpointsTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Puedes crear aquí datos de prueba si tienes modelos

    def test_qr_endpoint(self):
        response = self.client.get('/actas/qr/')
        self.assertIn(response.status_code, [200, 405, 400])

    def test_getconfig_endpoint(self):
        response = self.client.get('/actas/getconfig/')
        self.assertIn(response.status_code, [200, 405, 400])

    def test_registerotp_endpoint(self):
        # Usar un UUID de prueba, el endpoint espera POST
        response = self.client.post('/actas/00000000-0000-0000-0000-000000000000/registerotp/')
        self.assertIn(response.status_code, [200, 404, 400, 405])

    def test_sendotp_endpoint(self):
        response = self.client.post('/actas/00000000-0000-0000-0000-000000000000/sendotp/')
        self.assertIn(response.status_code, [200, 404, 400, 405])

    def test_bfaresponse_endpoint(self):
        response = self.client.post('/actas/00000000-0000-0000-0000-000000000000/bfaresponse/')
        self.assertIn(response.status_code, [200, 404, 400, 405])

    def test_reject_endpoint(self):
        response = self.client.post('/actas/00000000-0000-0000-0000-000000000000/reject/')
        self.assertIn(response.status_code, [200, 404, 400, 405])
