from django import template

register = template.Library()


@register.filter
def pesos_chilenos(valor):
    return f"${format(valor, ',.0f').replace(',', '.')}"


@register.filter
def unidades_carrito(carrito):
    if not isinstance(carrito, dict):
        return 0
    return sum(
        cantidad
        for cantidad in carrito.values()
        if isinstance(cantidad, int) and cantidad > 0
    )
