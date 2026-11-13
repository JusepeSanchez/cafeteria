from django.contrib.auth import get_user_model
from django.test import TestCase


class AutenticacionTests(TestCase):
    def setUp(self):
        self.cliente = get_user_model().objects.create_user(
            username="cliente",
            password="prueba123",
        )

    def test_inicio_exige_autenticacion(self):
        response = self.client.get("/")

        self.assertRedirects(response, "/accounts/login/?next=/")

    def test_login_y_logout(self):
        response = self.client.post(
            "/accounts/login/",
            {"username": "cliente", "password": "prueba123"},
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.session.get_expiry_age(), 30 * 60)
        response = self.client.post("/accounts/logout/")
        self.assertRedirects(response, "/accounts/login/")

    def test_cliente_no_accede_al_admin(self):
        self.client.force_login(self.cliente)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)

    def test_menu_muestra_usuario_y_rol(self):
        self.client.force_login(self.cliente)

        response = self.client.get("/catalogo/")

        self.assertContains(response, "cliente (Cliente)")

    def test_sesion_expira_en_30_minutos(self):
        self.client.force_login(self.cliente)

        self.assertEqual(self.client.session.get_expiry_age(), 30 * 60)
