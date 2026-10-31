from django.contrib import admin

from .models import (
    AsignacionTurno,
    Bodega,
    Cargo,
    Categoria,
    CategoriaFinanciera,
    CentroCosto,
    Cliente,
    Compra,
    ComponenteReceta,
    ConsumoProduccion,
    ContratoLaboral,
    Departamento,
    Despacho,
    DespachoVenta,
    DetalleCompra,
    DetalleVenta,
    Empleado,
    LiquidacionSueldo,
    ListaPrecio,
    Marca,
    MetodoPago,
    MovimientoInventario,
    OrdenProduccion,
    PagoVenta,
    PeriodoNomina,
    PrecioProducto,
    Producto,
    ProductoProveedor,
    Proveedor,
    RecetaProduccion,
    TransaccionFinanciera,
    Transportista,
    Turno,
    UnidadMedida,
    Venta,
)


class PrecioInline(admin.TabularInline):
    model = PrecioProducto
    extra = 0


class ProveedorProductoInline(admin.TabularInline):
    model = ProductoProveedor
    extra = 0


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("sku", "nombre", "categoria", "marca", "precio_actual", "stock_actual", "activo")
    list_filter = ("categoria", "marca", "activo")
    search_fields = ("sku", "nombre", "descripcion")
    list_select_related = ("categoria", "marca", "unidad")
    readonly_fields = ("creado", "actualizado", "stock_actual", "precio_actual")
    inlines = (PrecioInline, ProveedorProductoInline)

    @admin.display(description="Precio")
    def precio_actual(self, obj):
        return obj.precio_vigente

    @admin.display(description="Stock")
    def stock_actual(self, obj):
        return obj.stock_total


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "fecha", "estado", "total_venta")
    list_filter = ("estado", "fecha")
    search_fields = ("numero", "cliente__nombre", "cliente__rut")

    @admin.display(description="Total")
    def total_venta(self, obj):
        return obj.total


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "proveedor", "bodega", "fecha", "estado", "total_compra")
    list_filter = ("estado", "bodega", "fecha")
    search_fields = ("numero", "proveedor__razon_social")

    @admin.display(description="Total")
    def total_compra(self, obj):
        return obj.total


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("fecha", "producto", "bodega", "tipo", "cantidad", "costo_unitario", "referencia")
    list_filter = ("tipo", "bodega", "fecha")
    search_fields = ("producto__sku", "producto__nombre", "referencia")
    date_hierarchy = "fecha"


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("rut", "nombres", "apellidos", "email", "fecha_ingreso", "activo")
    list_filter = ("activo", "fecha_ingreso")
    search_fields = ("rut", "nombres", "apellidos", "email")


@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    list_display = ("numero", "receta", "bodega", "cantidad_planificada", "cantidad_producida", "estado")
    list_filter = ("estado", "bodega", "fecha_inicio")
    search_fields = ("numero", "receta__codigo", "receta__producto_terminado__nombre")


@admin.register(TransaccionFinanciera)
class TransaccionFinancieraAdmin(admin.ModelAdmin):
    list_display = ("fecha", "categoria", "centro_costo", "concepto", "monto", "referencia")
    list_filter = ("categoria__tipo", "categoria", "centro_costo", "fecha")
    search_fields = ("concepto", "referencia")
    date_hierarchy = "fecha"


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("rut", "razon_social", "email", "telefono", "activo")
    list_filter = ("activo",)
    search_fields = ("rut", "razon_social", "email")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("rut", "nombre", "tipo", "email", "telefono")
    list_filter = ("tipo",)
    search_fields = ("rut", "nombre", "email")


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = ("numero", "transportista", "fecha", "estado", "costo")
    list_filter = ("estado", "fecha")
    search_fields = ("numero", "transportista__nombre", "transportista__patente")


@admin.register(ContratoLaboral)
class ContratoLaboralAdmin(admin.ModelAdmin):
    list_display = ("empleado", "cargo", "fecha_inicio", "fecha_fin", "sueldo_base", "horas_semanales")
    list_filter = ("cargo__departamento", "cargo", "fecha_inicio")
    search_fields = ("empleado__rut", "empleado__nombres", "empleado__apellidos")


admin.site.register(
    [
        AsignacionTurno,
        Bodega,
        Cargo,
        Categoria,
        CategoriaFinanciera,
        CentroCosto,
        ComponenteReceta,
        ConsumoProduccion,
        Departamento,
        DespachoVenta,
        DetalleCompra,
        DetalleVenta,
        LiquidacionSueldo,
        ListaPrecio,
        Marca,
        MetodoPago,
        PagoVenta,
        PeriodoNomina,
        PrecioProducto,
        ProductoProveedor,
        RecetaProduccion,
        Transportista,
        Turno,
        UnidadMedida,
    ]
)

admin.site.site_header = "Administración CrisSteel · CrisFerreterias"
admin.site.site_title = "CrisSteel · CrisFerreterias"
admin.site.index_title = "Operaciones y datos maestros"


