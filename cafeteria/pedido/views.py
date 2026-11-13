from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Categoria, Producto


@login_required
def inicio(request):
    if request.user.is_staff:
        return redirect("admin:index")
    return redirect("catalogo")


def cliente_requerido(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


@cliente_requerido
def catalogo(request):
    productos = Producto.objects.filter(
        disponible=True,
        categoria__activa=True,
    ).select_related("categoria")
    busqueda = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    if busqueda:
        productos = productos.filter(nombre__icontains=busqueda)
    if categoria_id.isdecimal():
        productos = productos.filter(categoria_id=int(categoria_id))
    elif categoria_id:
        productos = productos.none()

    return render(
        request,
        "pedido/catalogo.html",
        {
            "productos": productos,
            "categorias": Categoria.objects.filter(activa=True),
            "busqueda": busqueda,
            "categoria_seleccionada": categoria_id,
        },
    )


@cliente_requerido
@require_POST
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(
        Producto,
        pk=producto_id,
        disponible=True,
        categoria__activa=True,
    )
    carrito = request.session.get("carrito", {})
    cantidad_actual = carrito.get(str(producto.pk), 0)

    if producto.stock < 1:
        messages.error(request, "Este producto está agotado.")
    elif cantidad_actual + 1 > producto.stock:
        messages.error(request, "No hay suficiente stock para agregar otra unidad.")
    else:
        carrito[str(producto.pk)] = cantidad_actual + 1
        request.session["carrito"] = carrito
        messages.success(request, "Producto agregado al carrito.")

    return redirect("catalogo")
