from django.conf import settings
from django.db import models
from django.db.models import Q


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
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    disponible = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=Q(precio__gte=0),
                name="producto_precio_no_negativo",
            ),
        ]

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PREPARADO = "preparado", "Preparado"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Pedido #{self.pk} - {self.cliente}"

    @property
    def total(self):
        return sum(
            (detalle.subtotal for detalle in self.detalles.all()),
            start=0,
        )


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
                condition=Q(cantidad__gte=1),
                name="detalle_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=Q(precio_unitario__gte=0),
                name="detalle_precio_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.producto}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
