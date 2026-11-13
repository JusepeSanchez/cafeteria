from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, DetallePedido, Pedido, Producto


class SeguimientoPedidosTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.cliente = user_model.objects.create_user(username="cliente", password="prueba123")
        self.otro_cliente = user_model.objects.create_user(username="otro", password="prueba123")
        self.encargado = user_model.objects.create_user(
            username="encargado",
            password="prueba123",
            is_staff=True,
        )
        categoria = Categoria.objects.create(nombre="Cafés")
        self.producto = Producto.objects.create(
            codigo="CAF-001",
            categoria=categoria,
            nombre="Espresso",
            precio=Decimal("1500"),
            stock=1,
        )
        self.pedido = Pedido.objects.create(cliente=self.cliente, retiro_en=timezone.now())
        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal("1500"),
        )

    def test_cliente_no_puede_ver_el_pedido_de_otra_persona(self):
        self.client.force_login(self.otro_cliente)

        response = self.client.get(reverse("pedido_detalle", args=[self.pedido.pk]))

        self.assertEqual(response.status_code, 404)

    def test_cancelar_pedido_pendiente_repone_stock(self):
        self.client.force_login(self.cliente)

        response = self.client.post(reverse("cancelar_pedido", args=[self.pedido.pk]))

        self.assertEqual(response.status_code, 302)
        self.pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.CANCELADO)
        self.assertEqual(self.producto.stock, 3)

    def test_encargado_avanza_un_estado_por_operacion(self):
        self.client.force_login(self.encargado)
        url = reverse("avanzar_pedido", args=[self.pedido.pk])

        self.client.post(url)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_PREPARACION)
        self.client.post(url)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.LISTO)
        self.client.post(url)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.ENTREGADO)
        self.client.post(url)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.ENTREGADO)

    def test_pedido_del_dia_filtra_por_estado(self):
        self.client.force_login(self.encargado)

        response = self.client.get(
            reverse("pedidos_del_dia"),
            {"estado": Pedido.PENDIENTE},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Pedido #{self.pedido.pk}")
