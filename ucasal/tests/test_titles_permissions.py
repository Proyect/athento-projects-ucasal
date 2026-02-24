from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch


class TitlesPermissionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Grupo requerido por las vistas de títulos
        self.titulos_group, _ = Group.objects.get_or_create(name="Titulos")

        # Usuario sin grupo "Titulos"
        self.user_no_group = User.objects.create_user(
            username="user_no_group", password="pass1234"
        )

        # Usuario con grupo "Titulos"
        self.user_titulos = User.objects.create_user(
            username="user_titulos", password="pass1234"
        )
        self.user_titulos.groups.add(self.titulos_group)

    def _login_no_group(self):
        self.client.logout()
        self.client.login(username="user_no_group", password="pass1234")

    def _login_titulos(self):
        self.client.logout()
        self.client.login(username="user_titulos", password="pass1234")

    def test_anonymous_is_redirected_from_titles_list(self):
        response = self.client.get("/ui/titulos/", follow=False)
        # Debe redirigir al login
        self.assertIn(response.status_code, (301, 302))

    def test_user_without_group_is_redirected_from_titles_list(self):
        self._login_no_group()
        response = self.client.get("/ui/titulos/", follow=False)
        self.assertIn(response.status_code, (301, 302))

    def test_user_with_group_can_access_titles_list(self):
        self._login_titulos()
        response = self.client.get("/ui/titulos/")
        # La vista puede depender de servicios externos, por lo que
        # solo comprobamos que no sea un redirect a login
        self.assertNotIn(response.status_code, (301, 302))

    def test_api_titles_requires_group(self):
        url = "/ui/api/titulos/"

        # Anónimo: redirect a login
        response = self.client.get(url, follow=False)
        self.assertIn(response.status_code, (301, 302))

        # Usuario sin grupo: también redirect
        self._login_no_group()
        response = self.client.get(url, follow=False)
        self.assertIn(response.status_code, (301, 302))

        # Usuario con grupo: no debería redirigir
        self._login_titulos()
        response = self.client.get(url, follow=False)
        self.assertNotIn(response.status_code, (301, 302))

    def test_bulk_delete_requires_group(self):
        url = "/ui/api/titulos/bulk-delete/"
        payload = {"uuids": ["00000000-0000-0000-0000-000000000000"]}

        # Anónimo
        response = self.client.post(url, data=payload, content_type="application/json", follow=False)
        self.assertIn(response.status_code, (301, 302))

        # Usuario sin grupo
        self._login_no_group()
        response = self.client.post(url, data=payload, content_type="application/json", follow=False)
        self.assertIn(response.status_code, (301, 302))

        # Usuario con grupo: no debería redirigir (aunque pueda fallar la lógica interna)
        self._login_titulos()
        response = self.client.post(url, data=payload, content_type="application/json", follow=False)
        self.assertNotIn(response.status_code, (301, 302))

    @patch("ucasal.views_ui.UcasalServices.create_file")
    def test_upload_title_view_success(self, mock_create_file):
        """Un usuario del grupo Titulos puede subir un archivo y la vista procesa OK."""
        self._login_titulos()
        mock_create_file.return_value = {"success": True, "uuid": "11111111-1111-1111-1111-111111111111"}

        file_content = b"dummy pdf content"
        uploaded = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")

        response = self.client.post(
            "/ui/titulos/nuevo/",
            {
                "file": uploaded,
                "filename": "test.pdf",
                "doctype": "form_titulo",
                "metadatas": "{}",
            },
        )

        # La vista debería devolver 200 y llamar al servicio
        self.assertEqual(response.status_code, 200)
        mock_create_file.assert_called_once()

    @patch("ucasal.views_ui.UcasalServices.get_file")
    def test_title_detail_view_uses_service(self, mock_get_file):
        """La vista de detalle de título usa UcasalServices.get_file y es accesible para el grupo."""
        self._login_titulos()
        mock_get_file.return_value = {"uuid": "22222222-2222-2222-2222-222222222222", "filename": "detail.pdf"}

        uuid = "22222222-2222-2222-2222-222222222222"
        response = self.client.get(f"/ui/titulos/{uuid}/")

        self.assertEqual(response.status_code, 200)
        mock_get_file.assert_called_once()

    @patch("ucasal.views_ui.UcasalServices.delete_file")
    def test_delete_title_view_redirects_after_delete(self, mock_delete_file):
        """La vista de borrado de título llama al servicio y redirige a la lista."""
        self._login_titulos()
        uuid = "33333333-3333-3333-3333-333333333333"

        response = self.client.post(f"/ui/titulos/{uuid}/delete/", follow=False)

        # Debe realizar redirect (302) hacia la lista de títulos
        self.assertIn(response.status_code, (301, 302))
        mock_delete_file.assert_called_once()
