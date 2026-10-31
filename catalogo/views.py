import json
from decimal import Decimal

from django.apps import apps
from django.db import connection, transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Bodega,
    Categoria,
    CategoriaFinanciera,
    CentroCosto,
    Cliente,
    Compra,
    ContratoLaboral,
    DetalleCompra,
    DetalleVenta,
    Empleado,
    MetodoPago,
    MovimientoInventario,
    OrdenProduccion,
    PagoVenta,
    PrecioProducto,
    Producto,
    ProductoProveedor,
    TransaccionFinanciera,
    Venta,
)


DECIMAL_FIELD = DecimalField(max_digits=16, decimal_places=2)
CATEGORIAS_UI = {
    "Herramientas eléctricas": ("electricas", "Eléctricas"),
    "Herramientas manuales": ("manuales", "Manuales"),
    "Fijaciones y adhesivos": ("fijaciones", "Fijaciones"),
    "Pinturas y terminaciones": ("pinturas", "Pinturas"),
    "Seguridad industrial": ("seguridad", "Seguridad"),
    "Construcción": ("construccion", "Construcción"),
    "Electricidad": ("electricidad", "Electricidad"),
    "Gasfitería": ("gasfiteria", "Gasfitería"),
}


def productos_con_indicadores():
    hoy = timezone.localdate()
    precio = (
        PrecioProducto.objects.filter(
            producto=OuterRef("pk"),
            lista__activa=True,
            vigente_desde__lte=hoy,
        )
        .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy))
        .order_by("-vigente_desde", "pk")
        .values("monto")[:1]
    )
    return (
        Producto.objects.filter(activo=True)
        .select_related("categoria", "marca", "unidad")
        .annotate(
            precio_db=Coalesce(
                Subquery(precio, output_field=DECIMAL_FIELD),
                Value(Decimal("0")),
                output_field=DECIMAL_FIELD,
            ),
            stock_db=Coalesce(
                Sum("movimientos__cantidad"),
                Value(Decimal("0")),
                output_field=DECIMAL_FIELD,
            ),
        )
    )


def suma_lineas(queryset, campo):
    expresion = ExpressionWrapper(F("cantidad") * F(campo), output_field=DECIMAL_FIELD)
    return queryset.aggregate(
        total=Coalesce(Sum(expresion), Value(Decimal("0")), output_field=DECIMAL_FIELD)
    )["total"]


def preparar_producto(producto):
    precio = getattr(producto, "precio_db", producto.precio_vigente)
    stock = getattr(producto, "stock_db", producto.stock_total)
    slug_ui, nombre_corto = CATEGORIAS_UI.get(
        producto.categoria.nombre,
        (producto.categoria.slug, producto.categoria.nombre),
    )
    return {
        "id": producto.pk,
        "sku": producto.sku,
        "nombre": producto.nombre,
        "categoria": producto.categoria.nombre,
        "precio": int(precio),
        "stock": int(stock),
        "descripcion": producto.descripcion,
        "slug_categoria": slug_ui,
        "categoria_corta": nombre_corto,
        "precio_formateado": f"${precio:,.0f}".replace(",", "."),
        "disponible": stock > 0,
        "imagen_base64": producto.imagen_base64,
        "unidad": producto.unidad.simbolo,
        "marca": producto.marca.nombre if producto.marca else "Sin marca",
        "punto_reorden": producto.punto_reorden,
    }


def preparar_categorias():
    return [
        {
            "nombre": categoria.nombre,
            "slug": CATEGORIAS_UI.get(categoria.nombre, (categoria.slug, categoria.nombre))[0],
            "cantidad": categoria.cantidad,
        }
        for categoria in Categoria.objects.filter(activa=True, productos__activo=True)
        .annotate(cantidad=Count("productos", filter=Q(productos__activo=True), distinct=True))
        .order_by("nombre")
    ]


def preparar_contexto_catalogo():
    queryset = productos_con_indicadores().order_by("pk")
    productos = [preparar_producto(producto) for producto in queryset]
    return {
        "productos": productos,
        "resumen": {
            "total": len(productos),
            "con_stock": sum(1 for producto in productos if producto["stock"] > 0),
            "sin_stock": sum(1 for producto in productos if producto["stock"] <= 0),
            "categorias": Categoria.objects.filter(activa=True, productos__activo=True)
            .distinct()
            .count(),
        },
        "categorias": preparar_categorias(),
        "origen_datos": "MariaDB XAMPP · CrisFerreterias · Django ORM",
    }


def lista_productos(request):
    return render(request, "catalogo/lista.html", preparar_contexto_catalogo())


def punto_venta(request):
    contexto = preparar_contexto_catalogo()
    contexto["caja"] = "01"
    return render(request, "catalogo/punto_venta.html", contexto)


def detalle_producto(request, producto_id):
    producto = get_object_or_404(
        productos_con_indicadores().prefetch_related("proveedores_producto__proveedor"),
        pk=producto_id,
    )
    stock_bodegas = (
        Bodega.objects.filter(movimientos__producto=producto)
        .annotate(stock=Sum("movimientos__cantidad"))
        .order_by("codigo")
    )
    return render(
        request,
        "catalogo/detalle.html",
        {
            "producto": preparar_producto(producto),
            "stock_bodegas": stock_bodegas,
            "proveedores": producto.proveedores_producto.select_related("proveedor"),
        },
    )


def panel(request):
    productos = productos_con_indicadores()
    lineas = DetalleVenta.objects.exclude(venta__estado=Venta.Estado.ANULADA)
    ingresos = suma_lineas(lineas, "precio_unitario")
    costos = suma_lineas(lineas, "costo_unitario")
    return render(
        request,
        "catalogo/panel.html",
        {
            "productos": productos.count(),
            "stock": MovimientoInventario.objects.aggregate(
                total=Coalesce(Sum("cantidad"), Value(Decimal("0")), output_field=DECIMAL_FIELD)
            )["total"],
            "ventas": Venta.objects.exclude(estado=Venta.Estado.ANULADA).count(),
            "ingresos": ingresos,
            "margen": ingresos - costos,
            "empleados": Empleado.objects.filter(activo=True).count(),
            "stock_bajo": productos.filter(stock_db__lte=F("punto_reorden")).order_by("stock_db")[:8],
            "ultimas_ventas": Venta.objects.select_related("cliente").order_by("-fecha")[:8],
        },
    )


def ventas(request):
    lineas = DetalleVenta.objects.exclude(venta__estado=Venta.Estado.ANULADA)
    ingresos = suma_lineas(lineas, "precio_unitario")
    costos = suma_lineas(lineas, "costo_unitario")
    return render(
        request,
        "catalogo/modulos/ventas.html",
        {
            "ventas": Venta.objects.select_related("cliente").prefetch_related("detalles").order_by("-fecha")[:30],
            "ingresos": ingresos,
            "costos": costos,
            "margen": ingresos - costos,
            "clientes": Venta.objects.values("cliente").distinct().count(),
        },
    )


def logistica(request):
    compras = DetalleCompra.objects.exclude(compra__estado=Compra.Estado.ANULADA)
    return render(
        request,
        "catalogo/modulos/logistica.html",
        {
            "bodegas": Bodega.objects.annotate(
                stock=Coalesce(Sum("movimientos__cantidad"), Value(Decimal("0")), output_field=DECIMAL_FIELD)
            ).order_by("codigo"),
            "compras": Compra.objects.select_related("proveedor", "bodega").prefetch_related("detalles").order_by("-fecha")[:20],
            "costo_compras": suma_lineas(compras, "costo_unitario"),
            "movimientos": MovimientoInventario.objects.select_related("producto", "bodega").order_by("-fecha")[:20],
            "stock_bajo": productos_con_indicadores().filter(stock_db__lte=F("punto_reorden")).order_by("stock_db")[:12],
        },
    )


def recursos_humanos(request):
    hoy = timezone.localdate()
    contratos = (
        ContratoLaboral.objects.select_related("empleado", "cargo", "cargo__departamento")
        .filter(fecha_inicio__lte=hoy)
        .filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy))
    )
    return render(
        request,
        "catalogo/modulos/rrhh.html",
        {
            "contratos": contratos,
            "empleados": Empleado.objects.filter(activo=True).count(),
            "departamentos": contratos.values("cargo__departamento").distinct().count(),
            "nomina": contratos.aggregate(
                total=Coalesce(Sum("sueldo_base"), Value(Decimal("0")), output_field=DECIMAL_FIELD)
            )["total"],
        },
    )


def produccion(request):
    ordenes = OrdenProduccion.objects.select_related(
        "receta", "receta__producto_terminado", "bodega"
    ).prefetch_related("consumos")
    return render(
        request,
        "catalogo/modulos/produccion.html",
        {
            "ordenes": ordenes.order_by("-fecha_inicio")[:20],
            "planificadas": ordenes.filter(estado=OrdenProduccion.Estado.PLANIFICADA).count(),
            "proceso": ordenes.filter(estado=OrdenProduccion.Estado.PROCESO).count(),
            "completadas": ordenes.filter(estado=OrdenProduccion.Estado.COMPLETADA).count(),
        },
    )


def finanzas(request):
    transacciones = TransaccionFinanciera.objects.select_related("categoria", "centro_costo")
    resumen = transacciones.aggregate(
        ingresos=Coalesce(Sum("monto", filter=Q(categoria__tipo=CategoriaFinanciera.Tipo.INGRESO)), Value(Decimal("0")), output_field=DECIMAL_FIELD),
        costos=Coalesce(Sum("monto", filter=Q(categoria__tipo=CategoriaFinanciera.Tipo.COSTO)), Value(Decimal("0")), output_field=DECIMAL_FIELD),
        gastos=Coalesce(Sum("monto", filter=Q(categoria__tipo=CategoriaFinanciera.Tipo.GASTO)), Value(Decimal("0")), output_field=DECIMAL_FIELD),
    )
    resumen["resultado"] = resumen["ingresos"] - resumen["costos"] - resumen["gastos"]
    return render(
        request,
        "catalogo/modulos/finanzas.html",
        {"resumen": resumen, "transacciones": transacciones.order_by("-fecha")[:30]},
    )


def configuracion(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION(), DATABASE()")
        version, base = cursor.fetchone()
    return render(
        request,
        "catalogo/configuracion.html",
        {
            "motor": "MariaDB XAMPP",
            "version": version,
            "base": base,
            "caracteristicas": "utf8mb4 · transacciones",
            "modelos": len(list(apps.get_app_config("catalogo").get_models())),
        },
    )


def api_productos(request):
    productos = [preparar_producto(producto) for producto in productos_con_indicadores().order_by("nombre")]
    for producto in productos:
        producto.pop("imagen_base64", None)
        producto.pop("precio_formateado", None)
    return JsonResponse({"total": len(productos), "productos": productos}, json_dumps_params={"ensure_ascii": False})


@require_POST
def registrar_venta_pos(request):
    try:
        payload = json.loads(request.body)
        lineas = payload.get("items", [])
        if not lineas:
            raise ValueError("El carro está vacío.")
    except (json.JSONDecodeError, ValueError) as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=400)

    try:
        with transaction.atomic():
            cliente, _ = Cliente.objects.get_or_create(
                rut="66.666.666-6",
                defaults={"nombre": "Consumidor final", "tipo": Cliente.Tipo.PERSONA},
            )
            metodo, _ = MetodoPago.objects.get_or_create(nombre="Efectivo")
            bodega = Bodega.objects.get(codigo="TIENDA-01")
            numero = f"POS{timezone.now():%Y%m%d%H%M%S%f}"[:24]
            venta = Venta.objects.create(
                numero=numero,
                cliente=cliente,
                estado=Venta.Estado.PAGADA,
            )
            total = Decimal("0")
            costo_total = Decimal("0")
            for linea in lineas:
                cantidad = Decimal(str(linea.get("quantity", 0)))
                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser positiva.")
                producto = Producto.objects.select_for_update().get(
                    pk=linea.get("id"), activo=True
                )
                stock = producto.stock_total
                if stock < cantidad:
                    raise ValueError(
                        f"Stock insuficiente para {producto.nombre}: quedan {stock:,.0f}."
                    )
                precio = producto.precio_vigente
                relacion = (
                    ProductoProveedor.objects.filter(producto=producto)
                    .order_by("-preferente", "costo_ultimo")
                    .first()
                )
                costo = relacion.costo_ultimo if relacion else Decimal("0")
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    costo_unitario=costo,
                )
                MovimientoInventario.objects.create(
                    producto=producto,
                    bodega=bodega,
                    tipo=MovimientoInventario.Tipo.VENTA,
                    cantidad=-cantidad,
                    costo_unitario=costo,
                    referencia=f"{numero}-{producto.sku}",
                    observacion="Venta registrada en POS web",
                )
                total += cantidad * precio
                costo_total += cantidad * costo
            PagoVenta.objects.create(
                venta=venta,
                metodo=metodo,
                monto=total,
                referencia=f"PAGO-{numero}",
            )
            centro, _ = CentroCosto.objects.get_or_create(
                codigo="CC-VTA", defaults={"nombre": "Ventas"}
            )
            categoria_ingreso, _ = CategoriaFinanciera.objects.get_or_create(
                codigo="ING-VTA",
                defaults={
                    "nombre": "Ingresos por ventas",
                    "tipo": CategoriaFinanciera.Tipo.INGRESO,
                },
            )
            categoria_costo, _ = CategoriaFinanciera.objects.get_or_create(
                codigo="COS-MER",
                defaults={
                    "nombre": "Costo de mercadería",
                    "tipo": CategoriaFinanciera.Tipo.COSTO,
                },
            )
            TransaccionFinanciera.objects.create(
                categoria=categoria_ingreso,
                centro_costo=centro,
                concepto=f"Ingreso venta {numero}",
                monto=total,
                referencia=f"ING-{numero}",
            )
            if costo_total > 0:
                TransaccionFinanciera.objects.create(
                    categoria=categoria_costo,
                    centro_costo=centro,
                    concepto=f"Costo mercadería {numero}",
                    monto=costo_total,
                    referencia=f"COSTO-{numero}",
                )
    except (Producto.DoesNotExist, Bodega.DoesNotExist, ValueError) as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "numero": venta.numero,
            "fecha": timezone.localtime(venta.fecha).strftime("%d/%m/%Y %H:%M"),
            "total": int(total),
        }
    )
