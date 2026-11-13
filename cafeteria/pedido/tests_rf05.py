from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, Pedido, Producto


class CarritoYConfirmacionTests(TestCase):
    def setUp(self):
        self.cliente = get_user_model().objects.create_user(
            username="cliente",
            password="prueba123",
        )
        self.categoria = Categoria.objects.create(nombre="Cafés")
        self.producto = Producto.objects.create(
            codigo="CAF-001",
            categoria=self.categoria,
            nombre="Espresso",
            precio=Decimal("1500"),
            stock=20,
        )
        self.otro_producto = Producto.objects.create(
            codigo="CAF-002",
            categoria=self.categoria,
            nombre="Moka",
            precio=Decimal("2800"),
            stock=1,
        )
        self.client.force_login(self.cliente)

    def test_carrito_limita_a_diez_unidades_y_no_supera_stock(self):
        url = reverse("agregar_al_carrito", args=[self.producto.pk])
        for _ in range(10):
            self.client.post(url)
        self.client.post(url)

        self.assertEqual(self.client.session["carrito"], {str(self.producto.pk): 10})
        self.assertContains(self.client.get(reverse("carrito")), "10 / 10")

    def test_confirmacion_con_falta_de_stock_no_crea_pedido_ni_descuenta(self):
        for _ in range(2):
            self.client.post(reverse("agregar_al_carrito", args=[self.producto.pk]))
        self.client.post(reverse("agregar_al_carrito", args=[self.otro_producto.pk]))
        self.otro_producto.stock = 0
        self.otro_producto.save(update_fields=["stock"])
        ahora = timezone.make_aware(
            datetime(2026, 1, 2, 10, 0),
            timezone.get_current_timezone(),
        )

        with patch("pedido.forms.timezone.localtime", return_value=ahora), patch(
            "pedido.views.timezone.localtime",
            return_value=ahora,
        ):
            response = self.client.post(
                reverse("confirmar_pedido"),
                {"hora_retiro": "10:30", "observacion": ""},
                follow=True,
            )

        self.assertContains(response, "Moka")
        self.assertEqual(Pedido.objects.count(), 0)
        self.producto.refresh_from_db()
        self.otro_producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 20)
        self.assertEqual(self.otro_producto.stock, 0)
        self.assertIn(str(self.producto.pk), self.client.session["carrito"])

    def test_confirmacion_guarda_precio_vigente_y_descuenta_stock(self):
        for _ in range(2):
            self.client.post(reverse("agregar_al_carrito", args=[self.producto.pk]))
        ahora = timezone.make_aware(
            datetime(2026, 1, 2, 10, 0),
            timezone.get_current_timezone(),
        )

        with patch("pedido.forms.timezone.localtime", return_value=ahora), patch(
            "pedido.views.timezone.localtime",
            return_value=ahora,
        ):
            response = self.client.post(
                reverse("confirmar_pedido"),
                {"hora_retiro": "10:30", "observacion": "Sin azúcar"},
            )

        self.assertEqual(response.status_code, 302)
        pedido = Pedido.objects.get()
        detalle = pedido.detalles.get()
        self.assertEqual(detalle.precio_unitario, Decimal("1500"))
        self.assertEqual(pedido.total, Decimal("3000"))
        self.assertEqual(pedido.estado, Pedido.PENDIENTE)
        self.assertEqual(pedido.observacion, "Sin azúcar")
        self.assertEqual(self.client.session["carrito"], {})
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 18)

    def test_hora_fuera_del_horario_muestra_error_en_formulario(self):
        response = self.client.post(
            reverse("confirmar_pedido"),
            {"hora_retiro": "07:59", "observacion": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "entre las 08:00 y las 18:00")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_hora_con_menos_de_veinte_minutos_muestra_error(self):
        ahora = timezone.make_aware(
            datetime(2026, 1, 2, 10, 0),
            timezone.get_current_timezone(),
        )
        with patch("pedido.forms.timezone.localtime", return_value=ahora):
            response = self.client.post(
                reverse("confirmar_pedido"),
                {"hora_retiro": "10:19", "observacion": ""},
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "al menos 20 minutos")
