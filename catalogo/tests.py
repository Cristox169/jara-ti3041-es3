import json

from django.contrib import admin
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management import get_commands
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from .models import MovimientoInventario, Producto, Venta


class CrisFerreteriasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("poblar_crisferreterias", verbosity=0)

    def test_backend_configurado(self):
        self.assertEqual(connection.vendor, "mysql")
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION(), DATABASE()")
            version, database = cursor.fetchone()
        self.assertIn("MariaDB", version)
        self.assertEqual(database.lower(), "crisferreterias_test")

    def test_hay_40_productos_normalizados(self):
        self.assertEqual(Producto.objects.filter(activo=True).count(), 40)
        producto = Producto.objects.select_related("categoria", "unidad").first()
        self.assertTrue(producto.sku)
        self.assertTrue(producto.categoria.nombre)
        self.assertGreaterEqual(producto.precio_vigente, 0)
        self.assertTrue(producto.imagen_base64.startswith("data:image/"))
        self.assertEqual(Producto.objects.exclude(imagen_base64="").count(), 40)
        self.assertFalse(any(campo.name in {"precio", "stock"} for campo in Producto._meta.fields))

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
        self.assertContains(listado, "MariaDB XAMPP activa")
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
        usuario = authenticate(username="admin", password="jarax")
        self.assertIsNotNone(usuario)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)

    def test_runserver_personalizado_es_activo(self):
        self.assertEqual(get_commands()["runserver"], "catalogo")


class PoblamientoIdempotenteTests(TestCase):
    def test_poblamiento_no_duplica_productos(self):
        call_command("poblar_crisferreterias", verbosity=0)
        call_command("poblar_crisferreterias", verbosity=0)
        self.assertEqual(Producto.objects.filter(activo=True).count(), 40)
