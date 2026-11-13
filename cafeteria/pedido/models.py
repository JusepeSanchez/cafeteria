from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo = models.CharField(
        max_length=7,
        unique=True,
        validators=[RegexValidator(r"^CAF-\d{3}$", "Usa el formato CAF-000.")],
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(100), MaxValueValidator(20000)],
    )
    stock = models.PositiveIntegerField(default=0)
    disponible = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio__gte=100, precio__lte=20000),
                name="producto_precio_rango_valido",
            )
        ]

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    PENDIENTE = "pendiente"
    EN_PREPARACION = "en_preparacion"
    LISTO = "listo"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"

    ESTADO_CHOICES = [
        (PENDIENTE, "Pendiente"),
        (EN_PREPARACION, "En preparación"),
        (LISTO, "Listo"),
        (ENTREGADO, "Entregado"),
        (CANCELADO, "Cancelado"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    retiro_en = models.DateTimeField()
    observacion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=PENDIENTE,
    )

    class Meta:
        ordering = ["-creado_en"]

    @property
    def total(self):
        total = Decimal("0.00")
        for detalle in self.detalles.all():
            total += detalle.precio_unitario * detalle.cantidad
        return total

    def __str__(self):
        return f"Pedido {self.pk} - Cliente: {self.cliente.username} - Estado: {self.estado}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_pedido",
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["pedido", "producto"],
                name="detalle_producto_unico_por_pedido",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="detalle_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name="detalle_precio_no_negativo",
            ),
        ]

    @property
    def subtotal_unitario(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"