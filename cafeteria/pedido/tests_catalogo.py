from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Producto


class CatalogoTests(TestCase):
    def setUp(self):
        self.cliente = get_user_model().objects.create_user(
            username="cliente",
            password="prueba123",
        )
        self.categoria = Categoria.objects.create(nombre="Cafés")
        self.otra_categoria = Categoria.objects.create(nombre="Tés")
        self.categoria_inactiva = Categoria.objects.create(
            nombre="Temporada",
            activa=False,
        )
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            nombre="Espresso",
            precio=Decimal("1500.00"),
            stock=2,
        )
        Producto.objects.create(
            categoria=self.categoria,
            nombre="Moka agotado",
            precio=Decimal("2800.00"),
            stock=0,
        )
        Producto.objects.create(
            categoria=self.categoria,
            nombre="Producto no disponible",
            precio=Decimal("2000.00"),
            stock=4,
            disponible=False,
        )
        Producto.objects.create(
            categoria=self.categoria_inactiva,
            nombre="Producto de temporada",
            precio=Decimal("2500.00"),
            stock=3,
        )
        self.client.force_login(self.cliente)

    def test_catalogo_muestra_productos_disponibles_y_pesos_chilenos(self):
        response = self.client.get(reverse("catalogo"))

        self.assertContains(response, "Espresso")
        self.assertContains(response, "$1.500")
        self.assertContains(response, "Moka agotado")
        self.assertContains(response, "Agotado")
        self.assertNotContains(response, "Producto no disponible")
        self.assertNotContains(response, "Producto de temporada")

    def test_busqueda_y_filtro_de_categoria(self):
        response = self.client.get(
            reverse("catalogo"),
            {"q": "Esp", "categoria": self.otra_categoria.pk},
        )
        self.assertNotContains(response, "Espresso")

        response = self.client.get(reverse("catalogo"), {"q": "Esp"})
        self.assertContains(response, "Espresso")
        self.assertNotContains(response, "Moka agotado")

    def test_categoria_mal_formada_no_falla(self):
        response = self.client.get(reverse("catalogo"), {"categoria": "invalida"})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Espresso")

    def test_carrito_rechaza_producto_sin_stock(self):
        agotado = Producto.objects.get(nombre="Moka agotado")

        response = self.client.post(
            reverse("agregar_al_carrito", args=[agotado.pk]),
        )

        self.assertRedirects(response, reverse("catalogo"))
        self.assertNotIn(str(agotado.pk), self.client.session.get("carrito", {}))

    def test_carrito_agrega_unidades_sin_superar_el_stock(self):
        url = reverse("agregar_al_carrito", args=[self.producto.pk])

        self.client.post(url)
        self.client.post(url)
        self.client.post(url)

        self.assertEqual(
            self.client.session["carrito"][str(self.producto.pk)],
            self.producto.stock,
        )

    def test_producto_no_disponible_no_se_puede_agregar(self):
        producto = Producto.objects.get(nombre="Producto no disponible")

        response = self.client.post(
            reverse("agregar_al_carrito", args=[producto.pk]),
        )

        self.assertEqual(response.status_code, 404)

    def test_encargado_no_accede_al_catalogo(self):
        encargado = get_user_model().objects.create_user(
            username="encargado",
            password="prueba123",
            is_staff=True,
        )
        self.client.force_login(encargado)

        response = self.client.get(reverse("catalogo"))

        self.assertEqual(response.status_code, 403)

    def test_catalogo_exige_autenticacion(self):
        self.client.logout()

        response = self.client.get(reverse("catalogo"))

        self.assertRedirects(response, "/accounts/login/?next=/catalogo/")
