from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.lista_productos, name="lista"),
    path("panel/", views.panel, name="panel"),
    path("punto-de-venta/", views.punto_venta, name="punto_venta"),
    path("punto-de-venta/registrar/", views.registrar_venta_pos, name="registrar_venta_pos"),
    path("producto/<int:producto_id>/", views.detalle_producto, name="detalle"),
    path("productos/nuevo/", views.producto_crear, name="producto_crear"),
    path("productos/<int:producto_id>/editar/", views.producto_editar, name="producto_editar"),
    path("productos/<int:producto_id>/eliminar/", views.producto_eliminar, name="producto_eliminar"),
    path("consultas/", views.consulta_cliente, name="consulta_cliente"),
    path("reportes/categorias/", views.reporte_categorias, name="reporte_categorias"),
    path("reportes/stock-critico/", views.reporte_stock_critico, name="reporte_stock_critico"),
    path("ventas/", views.ventas, name="ventas"),
    path("logistica/", views.logistica, name="logistica"),
    path("personas/", views.recursos_humanos, name="rrhh"),
    path("produccion/", views.produccion, name="produccion"),
    path("finanzas/", views.finanzas, name="finanzas"),
    path("configuracion/", views.configuracion, name="configuracion"),
    path("api/productos/", views.api_productos, name="api_productos"),
]
