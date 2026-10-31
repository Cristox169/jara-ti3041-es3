import json
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management import get_commands
from django.db import connection
from django.db.models import Avg, Q, Sum
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, ConsultaCliente, MovimientoInventario, Producto, UnidadMedida, Venta


class CrisFerreteriasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("poblar_crisferreterias", verbosity=0)

    def setUp(self):
        self.assertTrue(self.client.login(username="Cris", password="2598"))

    def test_backend_configurado(self):
        with connection.cursor() as cursor:
            if connection.vendor == "mysql":
                cursor.execute("SELECT VERSION(), DATABASE()")
                version, database = cursor.fetchone()
                self.assertIn("MariaDB", version)
                self.assertEqual(database.lower(), "crisferreterias_test")
            else:
                self.assertEqual(connection.vendor, "sqlite")
                cursor.execute("SELECT sqlite_version()")
                self.assertRegex(cursor.fetchone()[0], r"^\d+\.\d+")

    def test_hay_40_productos_normalizados(self):
        self.assertEqual(Producto.objects.filter(activo=True).count(), 40)
        producto = Producto.objects.select_related("categoria", "unidad").first()
        self.assertTrue(producto.sku)
        self.assertTrue(producto.categoria.nombre)
        self.assertGreaterEqual(producto.precio_vigente, 0)
        self.assertFalse(any(campo.name in {"precio", "stock"} for campo in Producto._meta.fields))
        self.assertGreaterEqual(producto.stock_ideal, producto.stock_minimo)

    def test_login_y_expiracion_por_inactividad(self):
        self.client.logout()
        anonimo = self.client.get("/")
        self.assertRedirects(anonimo, "/login/?next=/")
        for ruta in ("/panel/", "/punto-de-venta/", "/abastecimiento/", "/cotizaciones/", "/api/productos/"):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta["Location"].startswith("/login/?next="))
        login = self.client.get("/login/")
        self.assertEqual(login.status_code, 200)
        self.assertContains(login, "Bienvenido de vuelta.")
        self.assertContains(login, "7 minutos")
        self.assertTrue(self.client.login(username="Cris", password="2598"))
        session = self.client.session
        session["crissteel_last_activity"] = timezone.now().timestamp() - 421
        session.save()
        expirado = self.client.get("/")
        self.assertRedirects(expirado, "/login/?expired=1&next=/")

    def test_documentos_comerciales_y_abastecimiento_responden(self):
        for nombre in ("carrito", "cotizaciones", "ordenes_trabajo", "notas_credito", "abastecimiento"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(f"catalogo:{nombre}")).status_code, 200)

    def test_catalogo_detalle_y_api_consultan_bd(self):
        producto = Producto.objects.get(sku="HEL-001")
        listado = self.client.get("/")
        detalle = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        api = self.client.get(reverse("catalogo:api_productos"))
        self.assertEqual(listado.status_code, 200)
        self.assertTemplateUsed(listado, "catalogo/lista.html")
        self.assertContains(listado, producto.nombre)
        self.assertContains(listado, 'href="/admin/"')
        self.assertContains(listado, "Administración")
        self.assertContains(listado, "MariaDB activa" if connection.vendor == "mysql" else "SQLite local")
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, producto.sku)
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.json()["total"], 40)

    def test_todos_los_modulos_responden(self):
        for nombre in [
            "panel",
            "punto_venta",
            "ventas",
            "logistica",
            "rrhh",
            "produccion",
            "finanzas",
            "configuracion",
        ]:
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(f"catalogo:{nombre}")).status_code, 200)

    def test_pos_registra_venta_y_descuenta_stock(self):
        producto = Producto.objects.get(sku="HEL-001")
        stock_antes = producto.stock_total
        ventas_antes = Venta.objects.count()
        response = self.client.post(
            reverse("catalogo:registrar_venta_pos"),
            data=json.dumps({"items": [{"id": producto.pk, "quantity": 1}]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Venta.objects.count(), ventas_antes + 1)
        producto.refresh_from_db()
        self.assertEqual(producto.stock_total, stock_antes - 1)
        self.assertTrue(
            MovimientoInventario.objects.filter(
                producto=producto,
                referencia__startswith=response.json()["numero"],
            ).exists()
        )

    def test_admin_registra_entidades_operacionales(self):
        self.assertIn(Producto, admin.site._registry)
        self.assertIn(Venta, admin.site._registry)

    def test_poblamiento_crea_superusuario(self):
        usuario = authenticate(username="Cris", password="2598")
        self.assertIsNotNone(usuario)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)
        self.assertIsNone(authenticate(username="admin", password="jarax"))

    def test_runserver_personalizado_es_activo(self):
        self.assertEqual(get_commands()["runserver"], "catalogo")

    def test_crud_web_crea_edita_y_retira_producto(self):
        categoria = Categoria.objects.first()
        unidad = UnidadMedida.objects.first()
        crear = self.client.post(
            reverse("catalogo:producto_crear"),
            {
                "sku": "ES3-001",
                "nombre": "Producto de prueba ES3",
                "descripcion": "Producto creado desde el formulario web.",
                "categoria": categoria.pk,
                "marca": "",
                "unidad": unidad.pk,
                "punto_reorden": 2,
                "stock_minimo": 2,
                "stock_ideal": 8,
                "imagen_url": "",
                "activo": "on",
                "precio": "12990",
                "stock": "4",
            },
        )
        self.assertEqual(crear.status_code, 302)
        producto = Producto.objects.get(sku="ES3-001")
        self.assertEqual(producto.precio_vigente, 12990)
        self.assertEqual(producto.stock_total, 4)
        editar = self.client.post(
            reverse("catalogo:producto_editar", args=[producto.pk]),
            {
                "sku": producto.sku,
                "nombre": "Producto ES3 editado",
                "descripcion": producto.descripcion,
                "categoria": categoria.pk,
                "marca": "",
                "unidad": unidad.pk,
                "punto_reorden": 2,
                "stock_minimo": 2,
                "stock_ideal": 8,
                "imagen_url": "",
                "activo": "on",
                "precio": "13990",
                "stock": "6",
            },
        )
        self.assertEqual(editar.status_code, 302)
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, "Producto ES3 editado")
        self.assertEqual(producto.stock_total, 6)
        retirar = self.client.post(reverse("catalogo:producto_eliminar", args=[producto.pk]))
        self.assertEqual(retirar.status_code, 302)
        producto.refresh_from_db()
        self.assertFalse(producto.activo)

    def test_reportes_orm_y_navegacion(self):
        categorias = self.client.get(reverse("catalogo:reporte_categorias"))
        stock = self.client.get(reverse("catalogo:reporte_stock_critico"))
        self.assertEqual(categorias.status_code, 200)
        self.assertContains(categorias, "Resumen por categoría")
        self.assertContains(categorias, "Precio promedio")
        self.assertEqual(stock.status_code, 200)
        self.assertContains(stock, "Stock crítico")
        self.assertContains(stock, "Reporte ORM 02")

        admin_login = self.client.login(username="Cris", password="2598")
        self.assertTrue(admin_login)
        admin_productos = self.client.get(reverse("admin:catalogo_producto_changelist"))
        self.assertEqual(admin_productos.status_code, 200)
        total_admin = admin_productos.context["cl"].result_count

        categorias_orm = categorias.context["categorias"]
        total_reporte = sum(item.cantidad_productos for item in categorias_orm)
        self.assertEqual(total_reporte, total_admin)

        for categoria in categorias_orm:
            productos = Producto.objects.filter(categoria=categoria, activo=True)
            esperado_cantidad = productos.count()
            esperado_stock = sum((producto.stock_total for producto in productos), Decimal("0"))
            esperado_promedio = productos.aggregate(
                promedio=Avg(
                    "precios__monto",
                    filter=Q(precios__lista__activa=True),
                )
            )["promedio"]
            self.assertEqual(categoria.cantidad_productos, esperado_cantidad)
            self.assertEqual(categoria.stock_total, esperado_stock)
            self.assertEqual(categoria.precio_promedio, esperado_promedio)

        criticos_reportados = stock.context["productos"]
        criticos_reportados_ids = {item["id"] for item in criticos_reportados}
        stock_por_producto = (
            MovimientoInventario.objects.filter(producto__activo=True)
            .values("producto_id")
            .annotate(total=Sum("cantidad"))
        )
        stock_por_producto = {fila["producto_id"]: fila["total"] for fila in stock_por_producto}
        criticos_esperados = {
            producto.pk
            for producto in Producto.objects.filter(activo=True)
            if stock_por_producto.get(producto.pk, Decimal("0")) < producto.stock_minimo
        }
        self.assertEqual(criticos_reportados_ids, criticos_esperados)

    def test_consulta_cliente_model_form_y_sesion(self):
        producto = Producto.objects.get(sku="HEL-001")
        invalida = self.client.post(
            reverse("catalogo:consulta_cliente"),
            {"nombre": "A", "correo": "correo-invalido", "producto_interes": producto.pk, "mensaje": "corto"},
        )
        self.assertEqual(invalida.status_code, 200)
        self.assertEqual(ConsultaCliente.objects.count(), 0)
        self.assertContains(invalida, "Indica tu nombre completo.")
        self.assertContains(invalida, "Introduzca una")
        self.assertContains(invalida, "El mensaje debe tener al menos 10 caracteres.")

        campos_vacios = self.client.post(reverse("catalogo:consulta_cliente"), {})
        self.assertEqual(campos_vacios.status_code, 200)
        self.assertContains(campos_vacios, "Este campo es obligatorio.")
        self.assertEqual(ConsultaCliente.objects.count(), 0)

        valida = self.client.post(
            reverse("catalogo:consulta_cliente"),
            {
                "nombre": "Cliente de prueba",
                "correo": "cliente@example.com",
                "producto_interes": producto.pk,
                "mensaje": "Necesito conocer disponibilidad y despacho.",
            },
        )
        self.assertEqual(valida.status_code, 200)
        self.assertEqual(ConsultaCliente.objects.count(), 1)
        self.assertContains(valida, "Consulta enviada correctamente")
        for item in Producto.objects.order_by("pk")[:4]:
            self.client.get(reverse("catalogo:detalle", args=[item.pk]))
        self.assertEqual(len(self.client.session["productos_visitados"]), 3)


class PoblamientoIdempotenteTests(TestCase):
    def test_poblamiento_no_duplica_productos(self):
        call_command("poblar_crisferreterias", verbosity=0)
        call_command("poblar_crisferreterias", verbosity=0)
        self.assertEqual(Producto.objects.filter(activo=True).count(), 40)
