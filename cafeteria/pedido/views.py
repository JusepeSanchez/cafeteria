from datetime import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CategoriaForm, ConfirmarPedidoForm, ProductoForm
from .models import Categoria, DetallePedido, Pedido, Producto


def cliente_requerido(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def encargado_requerido(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
def inicio(request):
    if request.user.is_staff:
        return redirect("gestion_productos")
    return redirect("catalogo")


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


def _carrito_sesion(request):
    carrito = request.session.get("carrito", {})
    if not isinstance(carrito, dict):
        return {}
    limpio = {}
    for producto_id, cantidad in carrito.items():
        if str(producto_id).isdecimal() and isinstance(cantidad, int) and cantidad > 0:
            limpio[str(producto_id)] = cantidad
    return limpio


def _unidades_carrito(carrito):
    return sum(carrito.values())


@cliente_requerido
@require_POST
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(
        Producto,
        pk=producto_id,
        disponible=True,
        categoria__activa=True,
    )
    carrito = _carrito_sesion(request)
    cantidad_actual = carrito.get(str(producto.pk), 0)

    if producto.stock < 1:
        messages.error(request, f"{producto.nombre} está agotado.")
    elif cantidad_actual + 1 > producto.stock:
        messages.error(request, f"No hay suficiente stock de {producto.nombre}.")
    elif _unidades_carrito(carrito) >= 10:
        messages.error(request, "El carrito no puede superar 10 unidades.")
    else:
        carrito[str(producto.pk)] = cantidad_actual + 1
        request.session["carrito"] = carrito
        messages.success(request, "Producto agregado al carrito.")

    return redirect("catalogo")


@cliente_requerido
def carrito(request):
    carrito_sesion = _carrito_sesion(request)
    productos = Producto.objects.in_bulk(carrito_sesion.keys())
    items = []
    total = 0
    for producto_id, cantidad in carrito_sesion.items():
        producto = productos.get(int(producto_id))
        if producto is None:
            continue
        subtotal = producto.precio * cantidad
        items.append({"producto": producto, "cantidad": cantidad, "subtotal": subtotal})
        total += subtotal
    return render(
        request,
        "pedido/carrito.html",
        {
            "items": items,
            "total": total,
            "total_unidades": _unidades_carrito(carrito_sesion),
        },
    )


@cliente_requerido
@require_POST
def actualizar_carrito(request, producto_id):
    carrito_sesion = _carrito_sesion(request)
    producto = get_object_or_404(Producto, pk=producto_id)
    try:
        cantidad = int(request.POST.get("cantidad", ""))
    except (TypeError, ValueError):
        cantidad = 0

    otras_unidades = _unidades_carrito(carrito_sesion) - carrito_sesion.get(str(producto.pk), 0)
    if cantidad < 1:
        messages.error(request, "La cantidad debe ser al menos 1.")
    elif cantidad > producto.stock:
        messages.error(request, f"La cantidad supera el stock disponible de {producto.nombre}.")
    elif otras_unidades + cantidad > 10:
        messages.error(request, "El carrito no puede superar 10 unidades.")
    else:
        carrito_sesion[str(producto.pk)] = cantidad
        request.session["carrito"] = carrito_sesion
        messages.success(request, "Cantidad actualizada.")
    return redirect("carrito")


@cliente_requerido
@require_POST
def quitar_del_carrito(request, producto_id):
    carrito_sesion = _carrito_sesion(request)
    carrito_sesion.pop(str(producto_id), None)
    request.session["carrito"] = carrito_sesion
    messages.success(request, "Producto quitado del carrito.")
    return redirect("carrito")


@cliente_requerido
@require_POST
def vaciar_carrito(request):
    request.session["carrito"] = {}
    messages.success(request, "Carrito vaciado.")
    return redirect("carrito")


@cliente_requerido
def confirmar_pedido(request):
    carrito_sesion = _carrito_sesion(request)
    form = ConfirmarPedidoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not carrito_sesion:
            messages.error(request, "El carrito está vacío.")
            return redirect("carrito")
        if _unidades_carrito(carrito_sesion) > 10:
            messages.error(request, "El carrito no puede superar 10 unidades.")
            return redirect("carrito")

        with transaction.atomic():
            productos = {
                str(producto.pk): producto
                for producto in Producto.objects.select_for_update()
                .filter(pk__in=[int(pk) for pk in carrito_sesion])
                .order_by("pk")
            }
            fallido = None
            for producto_id, cantidad in carrito_sesion.items():
                producto = productos.get(producto_id)
                if (
                    producto is None
                    or not producto.disponible
                    or not producto.categoria.activa
                    or producto.stock < cantidad
                ):
                    fallido = producto
                    nombre = producto.nombre if producto else f"Producto {producto_id}"
                    break

            if fallido is None:
                ahora = timezone.localtime()
                retiro_en = timezone.make_aware(
                    datetime.combine(ahora.date(), form.cleaned_data["hora_retiro"]),
                    timezone.get_current_timezone(),
                )
                pedido = Pedido.objects.create(
                    cliente=request.user,
                    retiro_en=retiro_en,
                    observacion=form.cleaned_data["observacion"],
                )
                for producto_id, cantidad in carrito_sesion.items():
                    producto = productos[producto_id]
                    DetallePedido.objects.create(
                        pedido=pedido,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio,
                    )
                    producto.stock -= cantidad
                    producto.save(update_fields=["stock"])

        if fallido is not None:
            messages.error(request, f"No hay stock suficiente o el producto no está disponible: {nombre}.")
            return redirect("carrito")

        request.session["carrito"] = {}
        messages.success(request, f"Pedido #{pedido.pk} confirmado.")
        return redirect("pedido_detalle", pedido_id=pedido.pk)

    return render(
        request,
        "pedido/confirmar_pedido.html",
        {"form": form, "total_unidades": _unidades_carrito(carrito_sesion)},
    )


@cliente_requerido
def mis_pedidos(request):
    pedidos = Pedido.objects.filter(cliente=request.user).prefetch_related("detalles__producto")
    return render(request, "pedido/mis_pedidos.html", {"pedidos": pedidos})


@cliente_requerido
def pedido_detalle(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("detalles__producto"),
        pk=pedido_id,
        cliente=request.user,
    )
    return render(request, "pedido/pedido_detalle.html", {"pedido": pedido})


@cliente_requerido
@require_POST
def cancelar_pedido(request, pedido_id):
    with transaction.atomic():
        pedido = get_object_or_404(
            Pedido.objects.select_for_update().prefetch_related("detalles__producto"),
            pk=pedido_id,
            cliente=request.user,
        )
        if pedido.estado != Pedido.PENDIENTE:
            messages.error(request, "Solo se pueden cancelar pedidos pendientes.")
            return redirect("pedido_detalle", pedido_id=pedido.pk)
        detalles = list(pedido.detalles.all())
        productos = {
            producto.pk: producto
            for producto in Producto.objects.select_for_update()
            .filter(pk__in=[detalle.producto_id for detalle in detalles])
            .order_by("pk")
        }
        for detalle in detalles:
            producto = productos[detalle.producto_id]
            producto.stock += detalle.cantidad
            producto.save(update_fields=["stock"])
        pedido.estado = Pedido.CANCELADO
        pedido.save(update_fields=["estado"])
    messages.success(request, "Pedido cancelado; el stock fue repuesto.")
    return redirect("pedido_detalle", pedido_id=pedido.pk)


@encargado_requerido
def gestion_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, "pedido/gestion_categorias.html", {"categorias": categorias})


@encargado_requerido
def gestion_categoria_detalle(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    return render(request, "pedido/gestion_categoria_detalle.html", {"categoria": categoria})


@encargado_requerido
def gestion_categoria_crear(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        categoria = form.save()
        messages.success(request, "Categoría creada.")
        return redirect("gestion_categoria_detalle", categoria_id=categoria.pk)
    return render(request, "pedido/formulario.html", {"form": form, "titulo": "Crear categoría"})


@encargado_requerido
def gestion_categoria_editar(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == "POST" and form.is_valid():
        categoria = form.save()
        messages.success(request, "Categoría actualizada.")
        return redirect("gestion_categoria_detalle", categoria_id=categoria.pk)
    return render(request, "pedido/formulario.html", {"form": form, "titulo": "Editar categoría"})


@encargado_requerido
def gestion_categoria_eliminar(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    if request.method == "POST":
        try:
            categoria.delete()
        except ProtectedError:
            messages.error(request, "No se puede eliminar la categoría porque tiene productos asociados.")
            return redirect("gestion_categoria_detalle", categoria_id=categoria.pk)
        messages.success(request, "Categoría eliminada.")
        return redirect("gestion_categorias")
    return render(
        request,
        "pedido/confirmar_eliminacion.html",
        {"objeto": categoria, "tipo": "categoría"},
    )


@encargado_requerido
def gestion_productos(request):
    productos = Producto.objects.select_related("categoria").all()
    busqueda = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()
    disponibilidad = request.GET.get("disponible", "").strip()
    if busqueda:
        productos = productos.filter(Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda))
    if categoria_id.isdecimal():
        productos = productos.filter(categoria_id=int(categoria_id))
    elif categoria_id:
        productos = productos.none()
    if disponibilidad in ("1", "0"):
        productos = productos.filter(disponible=disponibilidad == "1")
    return render(
        request,
        "pedido/gestion_productos.html",
        {
            "productos": productos,
            "categorias": Categoria.objects.all(),
            "busqueda": busqueda,
            "categoria_seleccionada": categoria_id,
            "disponibilidad_seleccionada": disponibilidad,
        },
    )


@encargado_requerido
def gestion_producto_detalle(request, producto_id):
    producto = get_object_or_404(Producto.objects.select_related("categoria"), pk=producto_id)
    return render(request, "pedido/gestion_producto_detalle.html", {"producto": producto})


@encargado_requerido
def gestion_producto_crear(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(request, "Producto creado.")
        return redirect("gestion_producto_detalle", producto_id=producto.pk)
    return render(request, "pedido/formulario.html", {"form": form, "titulo": "Crear producto"})


@encargado_requerido
def gestion_producto_editar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(request, "Producto actualizado.")
        return redirect("gestion_producto_detalle", producto_id=producto.pk)
    return render(request, "pedido/formulario.html", {"form": form, "titulo": "Editar producto"})


@encargado_requerido
def gestion_producto_eliminar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    if request.method == "POST":
        try:
            producto.delete()
        except ProtectedError:
            messages.error(request, "No se puede eliminar el producto porque pertenece a pedidos.")
            return redirect("gestion_producto_detalle", producto_id=producto.pk)
        messages.success(request, "Producto eliminado.")
        return redirect("gestion_productos")
    return render(
        request,
        "pedido/confirmar_eliminacion.html",
        {"objeto": producto, "tipo": "producto"},
    )


@encargado_requerido
def pedidos_del_dia(request):
    pedidos = Pedido.objects.filter(
        creado_en__date=timezone.localdate(),
    ).select_related("cliente").prefetch_related("detalles__producto")
    estado = request.GET.get("estado", "").strip()
    estados_validos = {valor for valor, _ in Pedido.ESTADO_CHOICES}
    if estado in estados_validos:
        pedidos = pedidos.filter(estado=estado)
    elif estado:
        pedidos = pedidos.none()
    return render(
        request,
        "pedido/pedidos_encargado.html",
        {
            "pedidos": pedidos,
            "estado_seleccionado": estado,
            "estados": Pedido.ESTADO_CHOICES,
        },
    )


@encargado_requerido
@require_POST
def avanzar_pedido(request, pedido_id):
    siguientes = {
        Pedido.PENDIENTE: Pedido.EN_PREPARACION,
        Pedido.EN_PREPARACION: Pedido.LISTO,
        Pedido.LISTO: Pedido.ENTREGADO,
    }
    with transaction.atomic():
        pedido = get_object_or_404(
            Pedido.objects.select_for_update(),
            pk=pedido_id,
            creado_en__date=timezone.localdate(),
        )
        siguiente = siguientes.get(pedido.estado)
        if siguiente is None:
            messages.error(request, "Este pedido no se puede avanzar.")
        else:
            pedido.estado = siguiente
            pedido.save(update_fields=["estado"])
            messages.success(request, "Estado del pedido actualizado.")
    return redirect("pedidos_del_dia")
