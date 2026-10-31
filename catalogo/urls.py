from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.lista_productos, name="lista"),
    path("panel/", views.panel, name="panel"),
    path("punto-de-venta/", views.punto_venta, name="punto_venta"),
    path("punto-de-venta/registrar/", views.registrar_venta_pos, name="registrar_venta_pos"),
    path("producto/<int:producto_id>/", views.detalle_producto, name="detalle"),
    path("ventas/", views.ventas, name="ventas"),
    path("logistica/", views.logistica, name="logistica"),
    path("personas/", views.recursos_humanos, name="rrhh"),
    path("produccion/", views.produccion, name="produccion"),
    path("finanzas/", views.finanzas, name="finanzas"),
    path("configuracion/", views.configuracion, name="configuracion"),
    path("api/productos/", views.api_productos, name="api_productos"),
]
