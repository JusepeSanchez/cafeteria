from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, DetallePedido, Pedido, Producto


class GestionCatalogoTests(TestCase):
    def setUp(self):
        self.encargado = get_user_model().objects.create_user(
            username="encargado",
            password="prueba123",
            is_staff=True,
        )
        self.categoria = Categoria.objects.create(nombre="Cafés")
        self.producto = Producto.objects.create(
            codigo="CAF-001",
            categoria=self.categoria,
            nombre="Espresso",
            precio=Decimal("1500"),
            stock=3,
        )
        self.client.force_login(self.encargado)

    def test_crear_producto_rechaza_codigo_precio_y_stock_invalidos(self):
        response = self.client.post(
            reverse("gestion_producto_crear"),
            {
                "codigo": "CAFE-1",
                "categoria": self.categoria.pk,
                "nombre": "Producto inválido",
                "descripcion": "",
                "precio": "99",
                "stock": "-1",
                "disponible": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CAF-000")
        self.assertContains(response, "100")
        self.assertFalse(Producto.objects.filter(nombre="Producto inválido").exists())

    def test_listado_filtra_por_codigo_categoria_y_disponibilidad(self):
        Producto.objects.create(
            codigo="CAF-002",
            categoria=self.categoria,
            nombre="Moka",
            precio=Decimal("2800"),
            stock=0,
            disponible=False,
        )

        response = self.client.get(
            reverse("gestion_productos"),
            {"q": "CAF-002", "categoria": self.categoria.pk, "disponible": "0"},
        )

        self.assertContains(response, "Moka")
        self.assertNotContains(response, "Espresso")

    def test_categoria_protegida_muestra_error_y_no_falla(self):
        response = self.client.post(
            reverse("gestion_categoria_eliminar", args=[self.categoria.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tiene productos asociados")
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())

    def test_eliminar_categoria_solo_se_realiza_con_post(self):
        vacia = Categoria.objects.create(nombre="Vacía")

        response = self.client.get(reverse("gestion_categoria_eliminar", args=[vacia.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Categoria.objects.filter(pk=vacia.pk).exists())

    def test_producto_protegido_informa_error_al_eliminar(self):
        pedido = Pedido.objects.create(cliente=self.encargado, retiro_en=timezone.now())
        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("1500"),
        )

        response = self.client.post(
            reverse("gestion_producto_eliminar", args=[self.producto.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pertenece a pedidos")
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())
