import json
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.db import connection, transaction
from django.contrib import messages
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .imagenes_productos import PRODUCT_IMAGE_DATA
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
from .forms import ConsultaClienteForm, ProductoForm, sincronizar_precio_y_stock


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
        "imagen_base64": getattr(producto, "imagen_base64", "") or PRODUCT_IMAGE_DATA.get(producto.pk, ""),
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
        "origen_datos": (
            "MariaDB · CrisFerreterias · Django ORM"
            if connection.vendor == "mysql"
            else "SQLite local · CrisFerreterias · Django ORM"
        ),
    }


def lista_productos(request):
    return render(request, "catalogo/lista.html", preparar_contexto_catalogo())


def producto_crear(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                producto = form.save()
                sincronizar_precio_y_stock(producto, form.cleaned_data["precio"], form.cleaned_data["stock"])
            messages.success(request, f"Producto {producto.nombre} creado correctamente.")
            return redirect("catalogo:lista")
    else:
        form = ProductoForm(initial={"activo": True, "stock": 0, "precio": 0})
    return render(request, "catalogo/producto_form.html", {"form": form, "modo": "Crear"})


def producto_editar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            with transaction.atomic():
                producto = form.save()
                sincronizar_precio_y_stock(producto, form.cleaned_data["precio"], form.cleaned_data["stock"])
            messages.success(request, f"Producto {producto.nombre} actualizado correctamente.")
            return redirect("catalogo:lista")
    else:
        form = ProductoForm(instance=producto)
    return render(
        request,
        "catalogo/producto_form.html",
        {"form": form, "producto": producto, "modo": "Editar"},
    )


@require_POST
def producto_eliminar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    producto.activo = False
    producto.save(update_fields=["activo", "actualizado"])
    messages.success(request, f"Producto {producto.nombre} retirado del catálogo.")
    return redirect("catalogo:lista")


@require_http_methods(["GET", "POST"])
def consulta_cliente(request):
    if request.method == "POST":
        form = ConsultaClienteForm(request.POST)
        if form.is_valid():
            consulta = form.save()
            messages.success(request, f"Gracias, {consulta.nombre}. Recibimos tu consulta.")
            return render(request, "catalogo/consulta_cliente.html", {"form": ConsultaClienteForm(), "enviada": True})
    else:
        initial = {}
        producto_id = request.GET.get("producto")
        if producto_id and Producto.objects.filter(pk=producto_id, activo=True).exists():
            initial["producto_interes"] = producto_id
        form = ConsultaClienteForm(initial=initial)
    return render(request, "catalogo/consulta_cliente.html", {"form": form})


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
    visitados = request.session.get("productos_visitados", [])
    visitados = [int(pk) for pk in visitados if str(pk).isdigit() and int(pk) != producto.pk]
    visitados.insert(0, producto.pk)
    visitados = visitados[:3]
    request.session["productos_visitados"] = visitados
    recientes = list(
        Producto.objects.filter(pk__in=visitados, activo=True)
        .select_related("categoria")
        .order_by("nombre")
    )
    return render(
        request,
        "catalogo/detalle.html",
        {
            "producto": preparar_producto(producto),
            "stock_bodegas": stock_bodegas,
            "proveedores": producto.proveedores_producto.select_related("proveedor"),
            "productos_visitados": recientes,
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
        if connection.vendor == "mysql":
            cursor.execute("SELECT VERSION(), DATABASE()")
            version, base = cursor.fetchone()
            motor = "MariaDB"
            caracteristicas = "utf8mb4 · transacciones"
        else:
            cursor.execute("SELECT sqlite_version()")
            version = f"SQLite {cursor.fetchone()[0]}"
            base = Path(connection.settings_dict["NAME"]).name
            motor = "SQLite"
            caracteristicas = "archivo local · transacciones"
    return render(
        request,
        "catalogo/configuracion.html",
        {
            "motor": motor,
            "version": version,
            "base": base,
            "caracteristicas": caracteristicas,
            "modelos": len(list(apps.get_app_config("catalogo").get_models())),
        },
    )


def reporte_categorias(request):
    """Reporte 1: agrupación con Count, Avg y Sum resueltos por el ORM."""
    stock_por_categoria = (
        MovimientoInventario.objects.filter(
            producto__categoria=OuterRef("pk"), producto__activo=True
        )
        .values("producto__categoria")
        .annotate(total=Sum("cantidad"))
        .values("total")[:1]
    )
    categorias = (
        Categoria.objects.filter(activa=True)
        .annotate(
            cantidad_productos=Count(
                "productos", filter=Q(productos__activo=True), distinct=True
            ),
            stock_total=Coalesce(
                Subquery(stock_por_categoria, output_field=DECIMAL_FIELD),
                Value(Decimal("0")),
                output_field=DECIMAL_FIELD,
            ),
            precio_promedio=Coalesce(
                Avg(
                    "productos__precios__monto",
                    filter=Q(productos__activo=True, productos__precios__lista__activa=True),
                ),
                Value(Decimal("0")),
                output_field=DECIMAL_FIELD,
            ),
        )
        .order_by("nombre")
    )
    return render(request, "catalogo/reportes_categorias.html", {"categorias": categorias})


def reporte_stock_critico(request):
    """Reporte 2: filtro y orden de productos bajo su punto de reorden."""
    limite = request.GET.get("limite", "")
    productos = productos_con_indicadores()
    if limite:
        try:
            productos = productos.filter(stock_db__lte=Decimal(limite))
        except Exception:
            limite = ""
    else:
        productos = productos.filter(stock_db__lte=F("punto_reorden"))
    productos = productos.order_by("stock_db", "nombre")
    return render(
        request,
        "catalogo/reportes_stock.html",
        {"productos": [preparar_producto(producto) for producto in productos], "limite": limite},
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
