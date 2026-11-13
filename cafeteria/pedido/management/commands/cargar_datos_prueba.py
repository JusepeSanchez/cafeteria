from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from pedido.models import Categoria, Producto


class Command(BaseCommand):
    help = "Carga cuatro categorías, veinte productos y usuarios de demostración."

    def handle(self, *args, **options):
        categorias = [
            ("Cafés", "Cafés calientes y fríos."),
            ("Tés e infusiones", "Tés e infusiones variados."),
            ("Pastelería", "Productos dulces de pastelería."),
            ("Sandwiches", "Opciones saladas."),
        ]
        categorias_creadas = {}
        for nombre, descripcion in categorias:
            categoria, _ = Categoria.objects.update_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion, "activa": True},
            )
            categorias_creadas[nombre] = categoria

        productos = [
            ("Espresso", "Cafés", 1500, 20, True),
            ("Americano", "Cafés", 1800, 15, True),
            ("Cappuccino", "Cafés", 2500, 12, True),
            ("Latte", "Cafés", 2600, 8, True),
            ("Moka", "Cafés", 2800, 0, True),
            ("Té negro", "Tés e infusiones", 1400, 20, True),
            ("Té verde", "Tés e infusiones", 1600, 18, True),
            ("Manzanilla", "Tés e infusiones", 1300, 10, True),
            ("Menta", "Tés e infusiones", 1300, 9, True),
            ("Chai latte", "Tés e infusiones", 2400, 6, True),
            ("Croissant", "Pastelería", 1900, 14, True),
            ("Muffin de arándano", "Pastelería", 2200, 8, True),
            ("Kuchen de manzana", "Pastelería", 2900, 5, True),
            ("Brownie", "Pastelería", 2100, 0, True),
            ("Galleta de avena", "Pastelería", 1200, 16, True),
            ("Ave palta", "Sandwiches", 4200, 7, True),
            ("Jamón queso", "Sandwiches", 3500, 10, True),
            ("Vegetariano", "Sandwiches", 3900, 4, True),
            ("Atún", "Sandwiches", 4100, 3, True),
            ("Pollo pesto", "Sandwiches", 4500, 0, False),
        ]
        for indice, (nombre, nombre_categoria, precio, stock, disponible) in enumerate(productos, 1):
            Producto.objects.update_or_create(
                categoria=categorias_creadas[nombre_categoria],
                nombre=nombre,
                defaults={
                    "codigo": f"CAF-{indice:03d}",
                    "descripcion": f"{nombre} de la cafetería.",
                    "precio": precio,
                    "stock": stock,
                    "disponible": disponible,
                },
            )

        user_model = get_user_model()
        encargado, creado = user_model.objects.get_or_create(
            username="encargado",
            defaults={
                "first_name": "Encargado",
                "is_staff": True,
                "is_active": True,
            },
        )
        if creado:
            encargado.set_password("cafe1234")
            encargado.save()
        elif not encargado.is_staff:
            encargado.is_staff = True
            encargado.save(update_fields=["is_staff"])

        app_permissions = Permission.objects.filter(
            content_type__app_label="pedido",
        )
        encargado.user_permissions.add(*app_permissions)

        for username, nombre in (
            ("cliente1", "Cliente Uno"),
            ("cliente2", "Cliente Dos"),
        ):
            cliente, creado = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": nombre,
                    "is_staff": False,
                    "is_active": True,
                },
            )
            if creado:
                cliente.set_password("cafe1234")
                cliente.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Datos listos. Usuarios de prueba: encargado, cliente1 y cliente2 "
                "(contraseña: cafe1234)."
            )
        )
