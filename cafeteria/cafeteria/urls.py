"""
URL configuration for cafeteria project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from pedido import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("catalogo/", views.catalogo, name="catalogo"),
    path("carrito/", views.carrito, name="carrito"),
    path(
        "carrito/agregar/<int:producto_id>/",
        views.agregar_al_carrito,
        name="agregar_al_carrito",
    ),
    path("carrito/actualizar/<int:producto_id>/", views.actualizar_carrito, name="actualizar_carrito"),
    path("carrito/quitar/<int:producto_id>/", views.quitar_del_carrito, name="quitar_del_carrito"),
    path("carrito/vaciar/", views.vaciar_carrito, name="vaciar_carrito"),
    path("carrito/confirmar/", views.confirmar_pedido, name="confirmar_pedido"),
    path("pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("pedidos/<int:pedido_id>/", views.pedido_detalle, name="pedido_detalle"),
    path("pedidos/<int:pedido_id>/cancelar/", views.cancelar_pedido, name="cancelar_pedido"),
    path("gestion/categorias/", views.gestion_categorias, name="gestion_categorias"),
    path("gestion/categorias/crear/", views.gestion_categoria_crear, name="gestion_categoria_crear"),
    path("gestion/categorias/<int:categoria_id>/", views.gestion_categoria_detalle, name="gestion_categoria_detalle"),
    path("gestion/categorias/<int:categoria_id>/editar/", views.gestion_categoria_editar, name="gestion_categoria_editar"),
    path("gestion/categorias/<int:categoria_id>/eliminar/", views.gestion_categoria_eliminar, name="gestion_categoria_eliminar"),
    path("gestion/productos/", views.gestion_productos, name="gestion_productos"),
    path("gestion/productos/crear/", views.gestion_producto_crear, name="gestion_producto_crear"),
    path("gestion/productos/<int:producto_id>/", views.gestion_producto_detalle, name="gestion_producto_detalle"),
    path("gestion/productos/<int:producto_id>/editar/", views.gestion_producto_editar, name="gestion_producto_editar"),
    path("gestion/productos/<int:producto_id>/eliminar/", views.gestion_producto_eliminar, name="gestion_producto_eliminar"),
    path("gestion/pedidos/", views.pedidos_del_dia, name="pedidos_del_dia"),
    path("gestion/pedidos/<int:pedido_id>/avanzar/", views.avanzar_pedido, name="avanzar_pedido"),
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name="registration/login.html",
    ), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]
