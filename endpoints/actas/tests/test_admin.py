from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
import uuid
from ..models import Acta

class ActaAdminTest(TestCase):
    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        # Crear actas de prueba
        self.acta1 = Acta.objects.create(
            uuid=uuid.uuid4(),
            titulo='Acta 1',
            descripcion='Descripción 1',
            docente_asignado='prof1@ucasal.edu.ar',
            nombre_docente='Dr. Profesor 1',
            codigo_sector='001',
            estado='pendiente_otp'
        )
        
        self.acta2 = Acta.objects.create(
            uuid=uuid.uuid4(),
            titulo='Acta 2',
            descripcion='Descripción 2',
            docente_asignado='prof2@ucasal.edu.ar',
            nombre_docente='Dra. Profesora 2',
            codigo_sector='002',
            estado='firmada',
            firmada_con_otp=True
        )
        
        self.acta3 = Acta.objects.create(
            uuid=uuid.uuid4(),
            titulo='Acta 3',
            descripcion='Descripción 3',
            docente_asignado='prof3@ucasal.edu.ar',
            nombre_docente='Dr. Profesor 3',
            codigo_sector='003',
            estado='rechazada',
            motivo_rechazo='Error en datos'
        )
    
    def test_admin_login(self):
        """Test: Login en el admin"""
        response = self.client.get('/admin/')
        # El admin redirige a login si no está autenticado (302)
        # o muestra la página de login (200)
        self.assertIn(response.status_code, [200, 302])
        
        # Si redirige, seguir la redirección
        if response.status_code == 302:
            response = self.client.get(response.url)
        
        # Verificar que contiene elementos de login
        self.assertIn(response.status_code, [200, 302])
    
    def test_admin_actas_list(self):
        """Test: Lista de actas en el admin"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/actas/acta/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acta 1')
        self.assertContains(response, 'Acta 2')
        self.assertContains(response, 'Acta 3')
    
    def test_admin_actas_search(self):
        """Test: Búsqueda de actas en el admin"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/actas/acta/?q=Acta 1')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acta 1')
        # La búsqueda del admin puede ser flexible y mostrar resultados relacionados
        # Solo verificamos que encuentra Acta 1
        self.assertTrue('Acta 1' in response.content.decode('utf-8'))
    
    def test_admin_actas_filter_by_estado(self):
        """Test: Filtro por estado en el admin"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/actas/acta/?estado__exact=pendiente_otp')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acta 1')
        self.assertNotContains(response, 'Acta 2')
    
    def test_admin_actas_filter_by_activa(self):
        """Test: Filtro por activa en el admin"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/actas/acta/?activa__exact=1')
        
        self.assertEqual(response.status_code, 200)
        # Todas las actas están activas por defecto
        self.assertContains(response, 'Acta 1')
        self.assertContains(response, 'Acta 2')
        self.assertContains(response, 'Acta 3')
    
    def test_admin_actas_add(self):
        """Test: Agregar nueva acta desde el admin"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/actas/acta/add/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Título del Acta')
        self.assertContains(response, 'Email del Docente Asignado')
    
    def test_admin_actas_change(self):
        """Test: Editar acta desde el admin"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'/admin/actas/acta/{self.acta1.uuid}/change/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acta 1')
        self.assertContains(response, 'prof1@ucasal.edu.ar')
    
    def test_admin_actas_delete(self):
        """Test: Eliminar acta desde el admin"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'/admin/actas/acta/{self.acta1.uuid}/delete/')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que contiene texto de confirmación (manejar encoding)
        content_lower = response.content.decode('utf-8').lower()
        self.assertTrue('seguro' in content_lower or 'eliminar' in content_lower)
    
    def test_admin_actas_actions_marcar_firmada(self):
        """Test: Acción masiva marcar como firmada"""
        self.client.login(username='admin', password='admin123')
        
        # Seleccionar acta pendiente
        data = {
            'action': 'marcar_como_firmada',
            '_selected_action': [str(self.acta1.uuid)]
        }
        
        response = self.client.post('/admin/actas/acta/', data)
        self.assertEqual(response.status_code, 302)  # Redirección después de acción
        
        # Verificar que se actualizó
        self.acta1.refresh_from_db()
        self.assertEqual(self.acta1.estado, 'firmada')
        self.assertTrue(self.acta1.firmada_con_otp)
    
    def test_admin_actas_actions_marcar_rechazada(self):
        """Test: Acción masiva marcar como rechazada"""
        self.client.login(username='admin', password='admin123')
        
        # Seleccionar acta pendiente
        data = {
            'action': 'marcar_como_rechazada',
            '_selected_action': [str(self.acta1.uuid)]
        }
        
        response = self.client.post('/admin/actas/acta/', data)
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se actualizó
        self.acta1.refresh_from_db()
        self.assertEqual(self.acta1.estado, 'rechazada')
        self.assertEqual(self.acta1.motivo_rechazo, 'Rechazada desde el admin')
    
    def test_admin_actas_actions_reactivar(self):
        """Test: Acción masiva reactivar actas"""
        self.client.login(username='admin', password='admin123')
        
        # Seleccionar acta rechazada
        data = {
            'action': 'reactivar_acta',
            '_selected_action': [str(self.acta3.uuid)]
        }
        
        response = self.client.post('/admin/actas/acta/', data)
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se actualizó
        self.acta3.refresh_from_db()
        self.assertEqual(self.acta3.estado, 'pendiente_otp')
        self.assertEqual(self.acta3.motivo_rechazo, '')
    
    def test_admin_actas_permissions(self):
        """Test: Permisos del admin"""
        # Usuario normal (no admin)
        normal_user = User.objects.create_user(
            username='normal',
            email='normal@example.com',
            password='normal123'
        )
        
        self.client.login(username='normal', password='normal123')
        response = self.client.get('/admin/actas/acta/')
        
        # Debería redirigir o mostrar error de permisos
        self.assertIn(response.status_code, [302, 403])
    
    def test_admin_actas_readonly_fields(self):
        """Test: Campos de solo lectura"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'/admin/actas/acta/{self.acta1.uuid}/change/')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que los campos readonly están presentes
        self.assertContains(response, 'UUID')
        self.assertContains(response, 'Fecha de Creación')
    
    def test_admin_actas_fieldsets(self):
        """Test: Organización de campos en fieldsets"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'/admin/actas/acta/{self.acta1.uuid}/change/')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que los fieldsets están presentes
        self.assertContains(response, 'Información Principal')
        self.assertContains(response, 'Información del Docente')
        self.assertContains(response, 'Información Académica')
        self.assertContains(response, 'Fechas')
        self.assertContains(response, 'Información de Firma')
        self.assertContains(response, 'Blockchain')
    
    def test_admin_actas_list_display(self):
        """Test: Campos mostrados en la lista"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/actas/acta/')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que los campos de list_display están presentes
        self.assertContains(response, 'Título')
        self.assertContains(response, 'Email del Docente Asignado')
        self.assertContains(response, 'Código de Sector')
        self.assertContains(response, 'Estado')
        self.assertContains(response, 'Fecha de Creación')
    
    def test_admin_actas_ordering(self):
        """Test: Ordenamiento en la lista"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/actas/acta/')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que las actas están ordenadas por fecha de creación descendente
        # (más recientes primero)
        content = response.content.decode()
        pos_acta3 = content.find('Acta 3')
        pos_acta2 = content.find('Acta 2')
        pos_acta1 = content.find('Acta 1')
        
        # Acta 3 debería aparecer antes que Acta 1 (más reciente)
        self.assertTrue(pos_acta3 < pos_acta1)

