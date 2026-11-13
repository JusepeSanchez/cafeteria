from django.contrib import admin

from .models import Categoria, DetallePedido, Pedido, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre", "descripcion")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "stock", "disponible")
    list_filter = ("categoria", "disponible")
    search_fields = ("nombre", "descripcion", "categoria__nombre")
    list_select_related = ("categoria",)


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    autocomplete_fields = ("producto",)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "creado_en", "estado")
    list_filter = ("estado", "creado_en")
    search_fields = ("cliente__username", "cliente__first_name", "cliente__last_name")
    list_select_related = ("cliente",)
    inlines = (DetallePedidoInline,)


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    list_filter = ("producto__categoria",)
    search_fields = ("pedido__id", "producto__nombre")
    autocomplete_fields = ("pedido", "producto")
