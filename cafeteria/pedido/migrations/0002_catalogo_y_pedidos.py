import django.core.validators
import django.db.models
import django.utils.timezone
from django.db import migrations, models
from decimal import Decimal


def asignar_codigos(apps, schema_editor):
    Producto = apps.get_model("pedido", "Producto")
    for indice, producto in enumerate(Producto.objects.order_by("pk").iterator(), 1):
        if indice > 999:
            raise RuntimeError("No se pueden asignar códigos CAF-000 únicos a más de 999 productos.")
        producto.codigo = f"CAF-{indice:03d}"
        producto.save(update_fields=["codigo"])


def migrar_estado_preparado(apps, schema_editor):
    Pedido = apps.get_model("pedido", "Pedido")
    Pedido.objects.filter(estado="preparado").update(estado="en_preparacion")


def revertir_estado_preparado(apps, schema_editor):
    Pedido = apps.get_model("pedido", "Pedido")
    Pedido.objects.filter(estado="en_preparacion").update(estado="preparado")


class Migration(migrations.Migration):

    dependencies = [
        ("pedido", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="codigo",
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.RunPython(asignar_codigos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="producto",
            name="codigo",
            field=models.CharField(
                max_length=7,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        r"^CAF-\d{3}$",
                        "Usa el formato CAF-000.",
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="producto",
            name="precio",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[
                    django.core.validators.MinValueValidator(100),
                    django.core.validators.MaxValueValidator(20000),
                ],
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="retiro_en",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pedido",
            name="observacion",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(migrar_estado_preparado, revertir_estado_preparado),
        migrations.AlterField(
            model_name="pedido",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("en_preparacion", "En preparación"),
                    ("listo", "Listo"),
                    ("entregado", "Entregado"),
                    ("cancelado", "Cancelado"),
                ],
                default="pendiente",
                max_length=20,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="producto",
            name="producto_precio_no_negativo",
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.CheckConstraint(
                condition=models.Q(precio__gte=Decimal("100"), precio__lte=Decimal("20000")),
                name="producto_precio_rango_valido",
            ),
        ),
    ]
