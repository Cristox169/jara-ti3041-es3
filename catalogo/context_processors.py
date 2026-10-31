from django.db import connection
from django.urls import reverse


NAVEGACION = [
    ("Catálogo", "catalogo:lista", "lista"),
    ("Panel", "catalogo:panel", "panel"),
    ("Punto de venta", "catalogo:punto_venta", "punto_venta"),
    ("Ventas", "catalogo:ventas", "ventas"),
    ("Logística", "catalogo:logistica", "logistica"),
    ("Personas", "catalogo:rrhh", "rrhh"),
    ("Producción", "catalogo:produccion", "produccion"),
    ("Finanzas", "catalogo:finanzas", "finanzas"),
    ("Configuración", "catalogo:configuracion", "configuracion"),
    ("Contacto", "catalogo:consulta_cliente", "consulta_cliente"),
    ("Administración", "admin:index", "admin"),
]

MENU_VENTAS = [
    ("Punto de venta", "catalogo:punto_venta", "punto_venta"),
    ("Carro de compra", "catalogo:carrito", "carrito"),
    ("Cotizaciones", "catalogo:cotizaciones", "cotizaciones"),
    ("Órdenes de trabajo", "catalogo:ordenes_trabajo", "ordenes_trabajo"),
    ("Notas de crédito", "catalogo:notas_credito", "notas_credito"),
    ("Ventas emitidas", "catalogo:ventas", "ventas"),
]

MENU_APPS = [
    ("Dashboard integral", "catalogo:panel", "panel"),
    ("Abastecimiento", "catalogo:abastecimiento", "abastecimiento"),
    ("Reporte por categorías", "catalogo:reporte_categorias", "reporte_categorias"),
    ("Stock crítico", "catalogo:reporte_stock_critico", "reporte_stock_critico"),
    ("Logística", "catalogo:logistica", "logistica"),
    ("Finanzas", "catalogo:finanzas", "finanzas"),
]

MENU_OPERACION = [
    ("Logística", "catalogo:logistica", "logistica"),
    ("Personas y RR. HH.", "catalogo:rrhh", "rrhh"),
    ("Producción", "catalogo:produccion", "produccion"),
    ("Configuración", "catalogo:configuracion", "configuracion"),
]

MENU_ANALITICA = [
    ("Dashboard integral", "catalogo:panel", "panel"),
    ("Abastecimiento", "catalogo:abastecimiento", "abastecimiento"),
    ("Reportes por categoría", "catalogo:reporte_categorias", "reporte_categorias"),
    ("Stock crítico", "catalogo:reporte_stock_critico", "reporte_stock_critico"),
    ("Finanzas", "catalogo:finanzas", "finanzas"),
]


def navegacion_global(request):
    es_mariadb = connection.vendor == "mysql"
    return {
        "NAV_ITEMS": [
            {"label": label, "url": reverse(route), "match": match}
            for label, route, match in NAVEGACION
        ],
        "NAV_VENTAS": [
            {"label": label, "url": reverse(route), "match": match}
            for label, route, match in MENU_VENTAS
        ],
        "NAV_APPS": [
            {"label": label, "url": reverse(route), "match": match}
            for label, route, match in MENU_APPS
        ],
        "NAV_OPERACION": [
            {"label": label, "url": reverse(route), "match": match}
            for label, route, match in MENU_OPERACION
        ],
        "NAV_ANALITICA": [
            {"label": label, "url": reverse(route), "match": match}
            for label, route, match in MENU_ANALITICA
        ],
        "SESSION_TIMEOUT_MINUTES": 7,
        "DB_STATUS": "MariaDB activa" if es_mariadb else "SQLite local",
        "DB_ENGINE_LABEL": "MariaDB" if es_mariadb else "SQLite",
        "DB_STACK": "Django + MariaDB · ORM · TI3041" if es_mariadb else "Django + SQLite · ORM · TI3041",
    }
