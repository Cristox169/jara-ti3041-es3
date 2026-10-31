import json
import os
from datetime import date, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from catalogo.imagenes_productos import PRODUCT_IMAGE_DATA
from catalogo.models import (
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


PREFIJOS = {
    "Herramientas eléctricas": "HEL",
    "Herramientas manuales": "HMA",
    "Fijaciones y adhesivos": "FIJ",
    "Pinturas y terminaciones": "PIN",
    "Seguridad industrial": "SEG",
    "Construcción": "CON",
    "Electricidad": "ELE",
    "Gasfitería": "GAS",
}


def leer_productos_base():
    ruta = settings.BASE_DIR / "productos.json"
    with ruta.open(encoding="utf-8") as archivo:
        return json.load(archivo)


class Command(BaseCommand):
    help = "Carga los 40 productos y datos integrales de CrisFerreterias sin duplicarlos."

    @transaction.atomic
    def handle(self, *args, **options):
        datos_base = leer_productos_base()
        unidad, _ = UnidadMedida.objects.update_or_create(
            simbolo="un", defaults={"nombre": "Unidad"}
        )
        marca, _ = Marca.objects.update_or_create(
            nombre="CrisSteel Selección", defaults={"pais_origen": "Chile"}
        )
        lista, _ = ListaPrecio.objects.update_or_create(
            nombre="Precio público",
            defaults={"moneda": "CLP", "activa": True},
        )
        central, _ = Bodega.objects.update_or_create(
            codigo="BOD-CENTRAL",
            defaults={
                "nombre": "Centro de distribución CrisSteel",
                "direccion": "Av. Industrial 3041, Santiago",
                "activa": True,
            },
        )
        tienda, _ = Bodega.objects.update_or_create(
            codigo="TIENDA-01",
            defaults={
                "nombre": "Sala de ventas CrisSteel",
                "direccion": "Av. Industrial 3041, Santiago",
                "activa": True,
            },
        )
        norte, _ = Bodega.objects.update_or_create(
            codigo="BOD-NORTE",
            defaults={
                "nombre": "Bodega zona norte",
                "direccion": "Camino Lo Echevers 850, Quilicura",
                "activa": True,
            },
        )

        proveedores = []
        for rut, razon, correo, telefono in [
            ("76.310.410-1", "Distribuidora Aceros del Sur SpA", "ventas@acerosdelsur.cl", "+56 2 2310 4100"),
            ("76.520.620-2", "Herramientas Andinas Ltda.", "pedidos@andinas.cl", "+56 2 2520 6200"),
            ("76.730.830-3", "Suministros Técnicos Chile", "contacto@suministrostecnicos.cl", "+56 2 2730 8300"),
            ("76.940.150-4", "Importadora Maestro SpA", "comercial@maestro.cl", "+56 2 2940 1500"),
        ]:
            proveedor, _ = Proveedor.objects.update_or_create(
                rut=rut,
                defaults={
                    "razon_social": razon,
                    "email": correo,
                    "telefono": telefono,
                    "direccion": "Región Metropolitana",
                    "activo": True,
                },
            )
            proveedores.append(proveedor)

        categorias = {}
        indices_categoria = {}
        productos = []
        hoy = timezone.localdate()
        for posicion, entrada in enumerate(datos_base):
            campos = entrada["fields"]
            categoria_nombre = campos["categoria"]
            if categoria_nombre not in categorias:
                categorias[categoria_nombre], _ = Categoria.objects.update_or_create(
                    slug=slugify(categoria_nombre),
                    defaults={"nombre": categoria_nombre, "activa": True},
                )
            indices_categoria[categoria_nombre] = indices_categoria.get(categoria_nombre, 0) + 1
            sku = f"{PREFIJOS[categoria_nombre]}-{indices_categoria[categoria_nombre]:03d}"
            producto, _ = Producto.objects.update_or_create(
                sku=sku,
                defaults={
                    "nombre": campos["nombre"],
                    "descripcion": campos["descripcion"],
                    "categoria": categorias[categoria_nombre],
                    "marca": marca,
                    "unidad": unidad,
                    "punto_reorden": 5,
                    "imagen_base64": PRODUCT_IMAGE_DATA.get(entrada["pk"], ""),
                    "activo": True,
                },
            )
            productos.append(producto)
            precio = Decimal(str(campos["precio"]))
            costo = (precio * Decimal("0.62")).quantize(Decimal("1"))
            stock = Decimal(str(campos["stock"]))
            PrecioProducto.objects.update_or_create(
                producto=producto,
                lista=lista,
                vigente_desde=hoy,
                defaults={"monto": precio, "vigente_hasta": None},
            )
            if stock:
                MovimientoInventario.objects.update_or_create(
                    producto=producto,
                    bodega=central if posicion % 3 else tienda,
                    referencia=f"CARGA-INICIAL-{sku}",
                    defaults={
                        "tipo": MovimientoInventario.Tipo.AJUSTE,
                        "cantidad": stock,
                        "costo_unitario": costo,
                        "observacion": "Inventario inicial CrisFerreterias",
                    },
                )
            proveedor = proveedores[posicion % len(proveedores)]
            ProductoProveedor.objects.update_or_create(
                producto=producto,
                proveedor=proveedor,
                defaults={
                    "codigo_proveedor": f"PRV-{sku}",
                    "plazo_entrega_dias": 2 + posicion % 6,
                    "costo_ultimo": costo,
                    "preferente": True,
                },
            )

        clientes = []
        for rut, nombre, tipo, correo in [
            ("15.111.111-1", "Camila Rojas", Cliente.Tipo.PERSONA, "camila@example.cl"),
            ("16.222.222-2", "Diego Muñoz", Cliente.Tipo.PERSONA, "diego@example.cl"),
            ("77.333.333-3", "Constructora Horizonte SpA", Cliente.Tipo.EMPRESA, "compras@horizonte.cl"),
            ("77.444.444-4", "Mantenciones Sur Ltda.", Cliente.Tipo.EMPRESA, "operaciones@mantencionsur.cl"),
        ]:
            cliente, _ = Cliente.objects.update_or_create(
                rut=rut,
                defaults={
                    "nombre": nombre,
                    "tipo": tipo,
                    "email": correo,
                    "telefono": "+56 9 5000 0000",
                },
            )
            clientes.append(cliente)

        efectivo, _ = MetodoPago.objects.get_or_create(nombre="Efectivo")
        tarjeta, _ = MetodoPago.objects.get_or_create(nombre="Tarjeta")
        transferencia, _ = MetodoPago.objects.get_or_create(nombre="Transferencia")
        ahora = timezone.now()
        ventas_datos = [
            ("CSV-0001", 0, [(6, 2), (14, 3)], tarjeta),
            ("CSV-0002", 2, [(0, 1), (28, 4)], transferencia),
            ("CSV-0003", 1, [(21, 2), (23, 2)], efectivo),
            ("CSV-0004", 3, [(32, 8), (33, 4)], transferencia),
            ("CSV-0005", 2, [(38, 4), (39, 4)], tarjeta),
        ]
        ventas = []
        for indice, (numero, cliente_idx, lineas, metodo) in enumerate(ventas_datos):
            fecha = ahora - timedelta(days=indice * 4)
            venta, _ = Venta.objects.update_or_create(
                numero=numero,
                defaults={
                    "cliente": clientes[cliente_idx],
                    "fecha": fecha,
                    "estado": Venta.Estado.PAGADA,
                    "descuento": 0,
                },
            )
            ventas.append(venta)
            total = Decimal("0")
            for producto_idx, cantidad in lineas:
                producto = productos[producto_idx]
                precio = producto.precio_vigente
                costo = (precio * Decimal("0.62")).quantize(Decimal("1"))
                detalle, _ = DetalleVenta.objects.update_or_create(
                    venta=venta,
                    producto=producto,
                    defaults={
                        "cantidad": cantidad,
                        "precio_unitario": precio,
                        "costo_unitario": costo,
                    },
                )
                total += detalle.subtotal
                MovimientoInventario.objects.update_or_create(
                    producto=producto,
                    bodega=central,
                    referencia=f"{numero}-{producto.sku}",
                    defaults={
                        "tipo": MovimientoInventario.Tipo.VENTA,
                        "cantidad": -Decimal(cantidad),
                        "costo_unitario": costo,
                        "fecha": fecha,
                        "observacion": "Salida asociada a venta",
                    },
                )
            PagoVenta.objects.update_or_create(
                venta=venta,
                metodo=metodo,
                referencia=f"PAGO-{numero}",
                defaults={"monto": total, "fecha": fecha},
            )

        for indice, (numero, proveedor_idx, bodega, lineas) in enumerate([
            ("OC-0001", 0, central, [(6, 12), (14, 20)]),
            ("OC-0002", 1, norte, [(0, 5), (1, 5)]),
            ("OC-0003", 2, central, [(32, 30), (33, 20)]),
        ]):
            fecha = ahora - timedelta(days=25 + indice * 5)
            compra, _ = Compra.objects.update_or_create(
                numero=numero,
                defaults={
                    "proveedor": proveedores[proveedor_idx],
                    "bodega": bodega,
                    "fecha": fecha,
                    "estado": Compra.Estado.RECIBIDA,
                },
            )
            for producto_idx, cantidad in lineas:
                producto = productos[producto_idx]
                costo = (producto.precio_vigente * Decimal("0.62")).quantize(Decimal("1"))
                DetalleCompra.objects.update_or_create(
                    compra=compra,
                    producto=producto,
                    defaults={"cantidad": cantidad, "costo_unitario": costo},
                )
                MovimientoInventario.objects.update_or_create(
                    producto=producto,
                    bodega=bodega,
                    referencia=f"{numero}-{producto.sku}",
                    defaults={
                        "tipo": MovimientoInventario.Tipo.COMPRA,
                        "cantidad": cantidad,
                        "costo_unitario": costo,
                        "fecha": fecha,
                        "observacion": "Recepción de compra",
                    },
                )

        departamentos = {}
        for nombre in ["Ventas", "Logística", "Administración y Finanzas", "Producción"]:
            departamentos[nombre], _ = Departamento.objects.get_or_create(nombre=nombre)
        cargos = {}
        for departamento, nombre in [
            ("Ventas", "Vendedor"),
            ("Logística", "Encargado de bodega"),
            ("Administración y Finanzas", "Analista contable"),
            ("Producción", "Maestro de taller"),
        ]:
            cargos[nombre], _ = Cargo.objects.get_or_create(
                departamento=departamentos[departamento], nombre=nombre
            )
        contratos = []
        empleados = []
        empleados_datos = [
            ("18.101.101-1", "Ana", "Pérez Soto", "ana@crissteel.cl", "Vendedor", 750000),
            ("17.202.202-2", "Mauricio", "Lagos Díaz", "mauricio@crissteel.cl", "Encargado de bodega", 880000),
            ("19.303.303-3", "Francisca", "Vera Ríos", "francisca@crissteel.cl", "Analista contable", 1050000),
            ("16.404.404-4", "Pedro", "Araya León", "pedro@crissteel.cl", "Maestro de taller", 920000),
        ]
        for rut, nombres, apellidos, email, cargo, sueldo in empleados_datos:
            empleado, _ = Empleado.objects.update_or_create(
                rut=rut,
                defaults={
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "email": email,
                    "telefono": "+56 9 6000 0000",
                    "fecha_ingreso": date(2025, 3, 1),
                    "activo": True,
                },
            )
            empleados.append(empleado)
            contrato, _ = ContratoLaboral.objects.update_or_create(
                empleado=empleado,
                fecha_inicio=date(2025, 3, 1),
                defaults={
                    "cargo": cargos[cargo],
                    "fecha_fin": None,
                    "sueldo_base": sueldo,
                    "horas_semanales": 44,
                },
            )
            contratos.append(contrato)
        turno, _ = Turno.objects.get_or_create(
            nombre="Jornada diurna",
            defaults={"hora_inicio": time(8, 30), "hora_fin": time(17, 30)},
        )
        for empleado in empleados:
            AsignacionTurno.objects.update_or_create(
                empleado=empleado, fecha=hoy, defaults={"turno": turno}
            )

        inicio_periodo = hoy.replace(day=1)
        fin_periodo = (inicio_periodo + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        periodo, _ = PeriodoNomina.objects.update_or_create(
            nombre=f"Nómina {inicio_periodo:%Y-%m}",
            defaults={
                "fecha_inicio": inicio_periodo,
                "fecha_fin": fin_periodo,
                "estado": PeriodoNomina.Estado.CERRADO,
            },
        )
        for contrato in contratos:
            descuento = (contrato.sueldo_base * Decimal("0.10")).quantize(Decimal("1"))
            LiquidacionSueldo.objects.update_or_create(
                periodo=periodo,
                contrato=contrato,
                defaults={
                    "total_haberes": contrato.sueldo_base,
                    "total_descuentos": descuento,
                    "liquido": contrato.sueldo_base - descuento,
                },
            )

        receta, _ = RecetaProduccion.objects.update_or_create(
            codigo="REC-MOR-01",
            version=1,
            defaults={
                "producto_terminado": productos[33],
                "rendimiento": 1,
                "activa": True,
            },
        )
        ComponenteReceta.objects.update_or_create(
            receta=receta, componente=productos[32], defaults={"cantidad": Decimal("0.75")}
        )
        ComponenteReceta.objects.update_or_create(
            receta=receta, componente=productos[19], defaults={"cantidad": Decimal("0.10")}
        )
        orden, _ = OrdenProduccion.objects.update_or_create(
            numero="OP-0001",
            defaults={
                "receta": receta,
                "bodega": central,
                "cantidad_planificada": 10,
                "cantidad_producida": 4,
                "fecha_inicio": hoy - timedelta(days=2),
                "estado": OrdenProduccion.Estado.PROCESO,
            },
        )
        for producto_idx, cantidad in [(32, Decimal("3")), (19, Decimal("0.40"))]:
            producto = productos[producto_idx]
            costo = (producto.precio_vigente * Decimal("0.62")).quantize(Decimal("1"))
            ConsumoProduccion.objects.update_or_create(
                orden=orden,
                producto=producto,
                defaults={"cantidad": cantidad, "costo_unitario": costo},
            )

        transportista, _ = Transportista.objects.update_or_create(
            rut="14.555.555-5",
            defaults={
                "nombre": "Carlos Medina",
                "patente": "KLBR22",
                "telefono": "+56 9 7000 0000",
            },
        )
        despacho, _ = Despacho.objects.update_or_create(
            numero="DES-0001",
            defaults={
                "transportista": transportista,
                "fecha": ahora,
                "estado": Despacho.Estado.RUTA,
                "costo": 8500,
            },
        )
        DespachoVenta.objects.update_or_create(despacho=despacho, venta=ventas[1])

        centros = {}
        for codigo, nombre in [
            ("CC-VTA", "Ventas"),
            ("CC-LOG", "Logística"),
            ("CC-RRHH", "Recursos humanos"),
            ("CC-PROD", "Producción"),
        ]:
            centros[codigo], _ = CentroCosto.objects.update_or_create(
                codigo=codigo, defaults={"nombre": nombre}
            )
        categorias_financieras = {}
        for codigo, nombre, tipo in [
            ("ING-VTA", "Ingresos por ventas", CategoriaFinanciera.Tipo.INGRESO),
            ("COS-MER", "Costo de mercadería", CategoriaFinanciera.Tipo.COSTO),
            ("GAS-REM", "Remuneraciones", CategoriaFinanciera.Tipo.GASTO),
            ("GAS-DES", "Despachos", CategoriaFinanciera.Tipo.GASTO),
        ]:
            categorias_financieras[codigo], _ = CategoriaFinanciera.objects.update_or_create(
                codigo=codigo, defaults={"nombre": nombre, "tipo": tipo}
            )
        for venta in ventas:
            costo_venta = sum(
                (detalle.cantidad * detalle.costo_unitario for detalle in venta.detalles.all()),
                Decimal("0"),
            )
            TransaccionFinanciera.objects.update_or_create(
                referencia=f"ING-{venta.numero}",
                defaults={
                    "fecha": venta.fecha,
                    "categoria": categorias_financieras["ING-VTA"],
                    "centro_costo": centros["CC-VTA"],
                    "concepto": f"Ingreso venta {venta.numero}",
                    "monto": venta.total,
                },
            )
            TransaccionFinanciera.objects.update_or_create(
                referencia=f"COSTO-{venta.numero}",
                defaults={
                    "fecha": venta.fecha,
                    "categoria": categorias_financieras["COS-MER"],
                    "centro_costo": centros["CC-VTA"],
                    "concepto": f"Costo mercadería {venta.numero}",
                    "monto": costo_venta,
                },
            )
        total_nomina = sum((contrato.sueldo_base for contrato in contratos), Decimal("0"))
        TransaccionFinanciera.objects.update_or_create(
            referencia=f"NOMINA-{inicio_periodo:%Y-%m}",
            defaults={
                "fecha": ahora,
                "categoria": categorias_financieras["GAS-REM"],
                "centro_costo": centros["CC-RRHH"],
                "concepto": f"Nómina base {inicio_periodo:%Y-%m}",
                "monto": total_nomina,
            },
        )
        TransaccionFinanciera.objects.update_or_create(
            referencia="DES-DES-0001",
            defaults={
                "fecha": ahora,
                "categoria": categorias_financieras["GAS-DES"],
                "centro_costo": centros["CC-LOG"],
                "concepto": "Despacho DES-0001",
                "monto": despacho.costo,
            },
        )

        usuario_admin = os.getenv("ADMIN_USERNAME", "admin")
        clave_admin = os.getenv("ADMIN_PASSWORD", "jarax")
        correo_admin = os.getenv("ADMIN_EMAIL", "admin@localhost")
        modelo_usuario = get_user_model()
        administrador, creado = modelo_usuario.objects.get_or_create(
            username=usuario_admin,
            defaults={"email": correo_admin},
        )
        administrador.is_staff = True
        administrador.is_superuser = True
        administrador.is_active = True
        if creado:
            administrador.set_password(clave_admin)
        administrador.save()

        self.stdout.write(
            self.style.SUCCESS(
                "CrisFerreterias cargada: 40 productos, datos de todas las áreas y acceso administrativo."
            )
        )
