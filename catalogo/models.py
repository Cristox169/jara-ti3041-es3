from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    pais_origen = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    simbolo = models.CharField(max_length=12, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "unidad de medida"
        verbose_name_plural = "unidades de medida"

    def __str__(self):
        return f"{self.nombre} ({self.simbolo})"


class Producto(models.Model):
    sku = models.CharField("SKU", max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, related_name="productos", null=True, blank=True
    )
    unidad = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, related_name="productos")
    punto_reorden = models.PositiveIntegerField(default=5)
    imagen_url = models.URLField("URL de imagen", blank=True)
    imagen_base64 = models.TextField("imagen Base64", blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "producto"
        verbose_name_plural = "productos"

    def __str__(self):
        return f"{self.nombre} ({self.sku})"

    def get_absolute_url(self):
        return reverse("productos:detalle", kwargs={"pk": self.pk})

    @property
    def precio_vigente(self):
        hoy = timezone.localdate()
        precio = self.precios.filter(
            lista__activa=True,
            vigente_desde__lte=hoy,
        ).filter(models.Q(vigente_hasta__isnull=True) | models.Q(vigente_hasta__gte=hoy)).order_by(
            "-vigente_desde", "lista__nombre"
        ).first()
        return precio.monto if precio else Decimal("0")

    @property
    def stock_total(self):
        return self.movimientos.aggregate(total=models.Sum("cantidad"))["total"] or Decimal("0")

    @property
    def disponible(self):
        return self.activo and self.stock_total > 0


class ListaPrecio(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    moneda = models.CharField(max_length=3, default="CLP")
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "lista de precios"
        verbose_name_plural = "listas de precios"

    def __str__(self):
        return f"{self.nombre} ({self.moneda})"


class PrecioProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="precios")
    lista = models.ForeignKey(ListaPrecio, on_delete=models.PROTECT, related_name="precios")
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    vigente_desde = models.DateField(default=timezone.localdate)
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-vigente_desde"]
        constraints = [
            models.UniqueConstraint(fields=["producto", "lista", "vigente_desde"], name="uq_precio_producto_lista_fecha")
        ]
        verbose_name = "precio de producto"
        verbose_name_plural = "precios de productos"

    def __str__(self):
        return f"{self.producto.sku} · {self.lista.nombre} · ${self.monto:,.0f}"


class Bodega(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=180)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        COMPRA = "COMPRA", "Entrada por compra"
        VENTA = "VENTA", "Salida por venta"
        PRODUCCION_ENTRADA = "PROD_ENT", "Entrada por producción"
        PRODUCCION_SALIDA = "PROD_SAL", "Consumo de producción"
        AJUSTE = "AJUSTE", "Ajuste de inventario"

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="movimientos")
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    fecha = models.DateTimeField(default=timezone.now)
    referencia = models.CharField(max_length=80, blank=True)
    observacion = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        indexes = [models.Index(fields=["producto", "bodega", "fecha"], name="idx_mov_prod_bod_fecha")]
        constraints = [models.CheckConstraint(check=~models.Q(cantidad=0), name="ck_mov_cantidad_no_cero")]
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"

    def __str__(self):
        return f"{self.producto.sku} · {self.tipo} · {self.cantidad}"


class Proveedor(models.Model):
    rut = models.CharField("RUT", max_length=15, unique=True)
    razon_social = models.CharField(max_length=140)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=180, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["razon_social"]

    def __str__(self):
        return self.razon_social


class ProductoProveedor(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="proveedores_producto")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="productos_proveedor")
    codigo_proveedor = models.CharField(max_length=40, blank=True)
    plazo_entrega_dias = models.PositiveSmallIntegerField(default=3)
    costo_ultimo = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    preferente = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["producto", "proveedor"], name="uq_producto_proveedor")]
        verbose_name = "producto por proveedor"
        verbose_name_plural = "productos por proveedor"

    def __str__(self):
        return f"{self.producto.sku} · {self.proveedor.razon_social}"


class Cliente(models.Model):
    class Tipo(models.TextChoices):
        PERSONA = "PERSONA", "Persona"
        EMPRESA = "EMPRESA", "Empresa"

    rut = models.CharField("RUT", max_length=15, unique=True)
    nombre = models.CharField(max_length=140)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.PERSONA)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PAGADA = "PAGADA", "Pagada"
        DESPACHADA = "DESPACHADA", "Despachada"
        ANULADA = "ANULADA", "Anulada"

    numero = models.CharField(max_length=24, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ventas")
    fecha = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.BORRADOR)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return self.numero

    @property
    def total(self):
        bruto = sum((linea.subtotal for linea in self.detalles.all()), Decimal("0"))
        return max(bruto - self.descuento, Decimal("0"))


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="detalles_venta")
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["venta", "producto"], name="uq_venta_producto")]
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    @property
    def margen(self):
        return self.cantidad * (self.precio_unitario - self.costo_unitario)

    def __str__(self):
        return f"{self.venta.numero} · {self.producto.sku}"


class MetodoPago(models.Model):
    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "método de pago"
        verbose_name_plural = "métodos de pago"

    def __str__(self):
        return self.nombre


class PagoVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="pagos")
    metodo = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, related_name="pagos")
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    fecha = models.DateTimeField(default=timezone.now)
    referencia = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "pago de venta"
        verbose_name_plural = "pagos de ventas"

    def __str__(self):
        return f"{self.venta.numero} · {self.metodo} · ${self.monto:,.0f}"


class Compra(models.Model):
    class Estado(models.TextChoices):
        EMITIDA = "EMITIDA", "Emitida"
        RECIBIDA = "RECIBIDA", "Recibida"
        ANULADA = "ANULADA", "Anulada"

    numero = models.CharField(max_length=24, unique=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="compras")
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="compras")
    fecha = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.EMITIDA)

    class Meta:
        ordering = ["-fecha"]

    @property
    def total(self):
        return sum((linea.subtotal for linea in self.detalles.all()), Decimal("0"))

    def __str__(self):
        return self.numero


class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="detalles_compra")
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["compra", "producto"], name="uq_compra_producto")]
        verbose_name = "detalle de compra"
        verbose_name_plural = "detalles de compra"

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario

    def __str__(self):
        return f"{self.compra.numero} · {self.producto.sku}"


class Transportista(models.Model):
    rut = models.CharField("RUT", max_length=15, unique=True)
    nombre = models.CharField(max_length=120)
    patente = models.CharField(max_length=12, unique=True)
    telefono = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} · {self.patente}"


class Despacho(models.Model):
    class Estado(models.TextChoices):
        PREPARACION = "PREPARACION", "En preparación"
        RUTA = "RUTA", "En ruta"
        ENTREGADO = "ENTREGADO", "Entregado"

    numero = models.CharField(max_length=24, unique=True)
    transportista = models.ForeignKey(Transportista, on_delete=models.PROTECT, related_name="despachos")
    fecha = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PREPARACION)
    costo = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return self.numero


class DespachoVenta(models.Model):
    despacho = models.ForeignKey(Despacho, on_delete=models.CASCADE, related_name="ventas_despachadas")
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="despachos_venta")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["despacho", "venta"], name="uq_despacho_venta")]
        verbose_name = "venta por despacho"
        verbose_name_plural = "ventas por despacho"

    def __str__(self):
        return f"{self.despacho.numero} · {self.venta.numero}"


class Departamento(models.Model):
    nombre = models.CharField(max_length=90, unique=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name="cargos")
    nombre = models.CharField(max_length=90)

    class Meta:
        ordering = ["departamento__nombre", "nombre"]
        constraints = [models.UniqueConstraint(fields=["departamento", "nombre"], name="uq_departamento_cargo")]

    def __str__(self):
        return f"{self.nombre} · {self.departamento.nombre}"


class Empleado(models.Model):
    rut = models.CharField("RUT", max_length=15, unique=True)
    nombres = models.CharField(max_length=90)
    apellidos = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=30, blank=True)
    fecha_ingreso = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["apellidos", "nombres"]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class ContratoLaboral(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="contratos")
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name="contratos")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    sueldo_base = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    horas_semanales = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(45)])

    class Meta:
        ordering = ["-fecha_inicio"]
        constraints = [models.UniqueConstraint(fields=["empleado", "fecha_inicio"], name="uq_contrato_empleado_inicio")]
        verbose_name = "contrato laboral"
        verbose_name_plural = "contratos laborales"

    def __str__(self):
        return f"{self.empleado} · {self.cargo}"


class Turno(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ["hora_inicio"]

    def __str__(self):
        return self.nombre


class AsignacionTurno(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="asignaciones_turno")
    turno = models.ForeignKey(Turno, on_delete=models.PROTECT, related_name="asignaciones")
    fecha = models.DateField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["empleado", "fecha"], name="uq_empleado_turno_fecha")]
        verbose_name = "asignación de turno"
        verbose_name_plural = "asignaciones de turnos"

    def __str__(self):
        return f"{self.empleado} · {self.fecha} · {self.turno}"


class PeriodoNomina(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        CERRADO = "CERRADO", "Cerrado"

    nombre = models.CharField(max_length=80, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ABIERTO)

    class Meta:
        ordering = ["-fecha_inicio"]
        verbose_name = "período de nómina"
        verbose_name_plural = "períodos de nómina"

    def __str__(self):
        return self.nombre


class LiquidacionSueldo(models.Model):
    periodo = models.ForeignKey(PeriodoNomina, on_delete=models.PROTECT, related_name="liquidaciones")
    contrato = models.ForeignKey(ContratoLaboral, on_delete=models.PROTECT, related_name="liquidaciones")
    total_haberes = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_descuentos = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    liquido = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["periodo", "contrato"], name="uq_periodo_contrato")]
        verbose_name = "liquidación de sueldo"
        verbose_name_plural = "liquidaciones de sueldo"

    def __str__(self):
        return f"{self.periodo} · {self.contrato.empleado}"


class RecetaProduccion(models.Model):
    codigo = models.CharField(max_length=24)
    producto_terminado = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="recetas_como_terminado")
    version = models.PositiveSmallIntegerField(default=1)
    rendimiento = models.DecimalField(max_digits=10, decimal_places=2, default=1, validators=[MinValueValidator(Decimal("0.01"))])
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo", "-version"]
        constraints = [models.UniqueConstraint(fields=["codigo", "version"], name="uq_receta_codigo_version")]
        verbose_name = "receta de producción"
        verbose_name_plural = "recetas de producción"

    def __str__(self):
        return f"{self.codigo} v{self.version} · {self.producto_terminado}"


class ComponenteReceta(models.Model):
    receta = models.ForeignKey(RecetaProduccion, on_delete=models.CASCADE, related_name="componentes")
    componente = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="usos_como_componente")
    cantidad = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["receta", "componente"], name="uq_receta_componente")]
        verbose_name = "componente de receta"
        verbose_name_plural = "componentes de recetas"

    def __str__(self):
        return f"{self.receta.codigo} · {self.componente.sku}"


class OrdenProduccion(models.Model):
    class Estado(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        PROCESO = "PROCESO", "En proceso"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    numero = models.CharField(max_length=24, unique=True)
    receta = models.ForeignKey(RecetaProduccion, on_delete=models.PROTECT, related_name="ordenes")
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="ordenes_produccion")
    cantidad_planificada = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    cantidad_producida = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    fecha_inicio = models.DateField(default=timezone.localdate)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PLANIFICADA)

    class Meta:
        ordering = ["-fecha_inicio"]
        verbose_name = "orden de producción"
        verbose_name_plural = "órdenes de producción"

    def __str__(self):
        return self.numero


class ConsumoProduccion(models.Model):
    orden = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name="consumos")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="consumos_produccion")
    cantidad = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["orden", "producto"], name="uq_orden_producto_consumo")]
        verbose_name = "consumo de producción"
        verbose_name_plural = "consumos de producción"

    @property
    def costo_total(self):
        return self.cantidad * self.costo_unitario

    def __str__(self):
        return f"{self.orden.numero} · {self.producto.sku}"


class CentroCosto(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "centro de costo"
        verbose_name_plural = "centros de costo"

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class CategoriaFinanciera(models.Model):
    class Tipo(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        COSTO = "COSTO", "Costo"
        GASTO = "GASTO", "Gasto"

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=8, choices=Tipo.choices)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "categoría financiera"
        verbose_name_plural = "categorías financieras"

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class TransaccionFinanciera(models.Model):
    fecha = models.DateTimeField(default=timezone.now)
    categoria = models.ForeignKey(CategoriaFinanciera, on_delete=models.PROTECT, related_name="transacciones")
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.PROTECT, related_name="transacciones")
    concepto = models.CharField(max_length=180)
    monto = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    referencia = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        indexes = [models.Index(fields=["fecha", "categoria"], name="idx_tx_fecha_categoria")]
        verbose_name = "transacción financiera"
        verbose_name_plural = "transacciones financieras"

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d} · {self.categoria} · ${self.monto:,.0f}"


