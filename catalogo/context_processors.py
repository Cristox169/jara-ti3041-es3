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


def navegacion_global(request):
    es_mariadb = connection.vendor == "mysql"
    return {
        "NAV_ITEMS": [
            {"label": label, "url": reverse(route), "match": match}
            for label, route, match in NAVEGACION
        ],
        "DB_STATUS": "MariaDB activa" if es_mariadb else "SQLite local",
        "DB_ENGINE_LABEL": "MariaDB" if es_mariadb else "SQLite",
        "DB_STACK": "Django + MariaDB · ORM · TI3041" if es_mariadb else "Django + SQLite · ORM · TI3041",
    }
