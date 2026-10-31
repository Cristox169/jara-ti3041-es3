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
    ("Administración", "admin:index", "admin"),
]


def navegacion_global(request):
    return {
        "NAV_ITEMS": [
            {"label": label, "url": reverse(route), "match": match}
            for label, route, match in NAVEGACION
        ],
        "DB_STATUS": "MariaDB XAMPP activa",
        "DB_ENGINE_LABEL": "MariaDB",
        "DB_STACK": "Django + MariaDB XAMPP · ORM · TI3041",
    }
