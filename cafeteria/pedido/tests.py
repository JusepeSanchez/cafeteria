from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from .admin import DetallePedidoInline
from .models import Categoria, DetallePedido, Pedido, Producto


class ModeloPedidoTests(TestCase):
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
            precio=Decimal("1500.00"),
            stock=3,
        )

    def test_categoria_con_productos_no_se_puede_eliminar(self):
        with self.assertRaises(ProtectedError):
            self.categoria.delete()

    def test_producto_en_pedido_no_se_puede_eliminar(self):
        pedido = Pedido.objects.create(cliente=self.cliente, retiro_en=timezone.now())
        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal("1500.00"),
        )

        with self.assertRaises(ProtectedError):
            self.producto.delete()

    def test_pedido_muestra_detalles_y_total(self):
        pedido = Pedido.objects.create(cliente=self.cliente, retiro_en=timezone.now())
        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal("1500.00"),
        )

        self.assertEqual(pedido.total, Decimal("3000.00"))
        self.assertIn(DetallePedido, admin.site._registry)
        self.assertIn(DetallePedidoInline, admin.site._registry[Pedido].inlines)


class DatosDePruebaTests(TestCase):
    def test_comando_carga_categorias_productos_y_usuarios(self):
        call_command("cargar_datos_prueba", verbosity=0)

        self.assertGreaterEqual(Categoria.objects.count(), 4)
        self.assertGreaterEqual(Producto.objects.count(), 20)
        self.assertTrue(Producto.objects.filter(stock=0).exists())
        self.assertTrue(Producto.objects.filter(disponible=False).exists())
        user_model = get_user_model()
        self.assertTrue(user_model.objects.get(username="encargado").is_staff)
        self.assertEqual(
            user_model.objects.filter(
                username__in=["cliente1", "cliente2"],
                is_staff=False,
            ).count(),
            2,
        )
