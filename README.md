# CrisSteel · CrisFerreterias

Sistema Django integral para una ferretería, construido sobre el proyecto ES2 original. Cubre catálogo, punto de venta persistente, compras, inventario, logística, recursos humanos, nómina, producción y análisis financiero. La entrega conserva MariaDB como motor principal de la evaluación y añade un modo SQLite portátil para ejecutarla sin configuración previa.

## Ejecución portátil

En Windows, ejecuta `iniciar_portatil.bat`. El iniciador crea el entorno virtual, instala las dependencias, prepara la base local, carga los datos y abre automáticamente:

- Sitio: <http://127.0.0.1:8000/>
- Administración: <http://127.0.0.1:8000/admin/>

También se puede iniciar manualmente:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py poblar_crisferreterias
.\.venv\Scripts\python.exe manage.py runserver
```

Al ejecutar `python manage.py runserver`, el propio `manage.py` muestra inmediatamente el enlace <http://127.0.0.1:8000/> y Django vuelve a mostrarlo cuando el puerto queda activo. En Windows, la página también se abre automáticamente. El archivo `ABRIR_CRISSTEEL.url` permite volver a abrirla con doble clic mientras el servidor siga ejecutándose. Usa `python manage.py runserver --no-browser` si no deseas abrir el navegador.

## Base de datos MariaDB

- Motor: MariaDB 11.4.3.
- Base: `CrisFerreterias`.
- Puerto local: `3307`, separado del MariaDB incluido en XAMPP.
- Juego de caracteres: `utf8mb4`.
- Configuración privada: `.env` (ignorada por Git).
- Esquema normalizado: [`docs/normalizacion_5fn.md`](docs/normalizacion_5fn.md).
- Consultas analíticas: [`connectBD/consultas.sql`](connectBD/consultas.sql).

`Producto` no almacena precio ni stock. El precio vigente se obtiene desde `PrecioProducto` y el inventario se deriva de `MovimientoInventario`. Las relaciones multivaluadas están descompuestas mediante tablas puente y los documentos usan cabecera/detalle.

## Inicio con MariaDB

Desde la carpeta del proyecto:

```powershell
.\scripts\iniciar_mariadb.ps1
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py poblar_crisferreterias
.\.venv\Scripts\python.exe manage.py runserver
```

O ejecutar `iniciar_crissteel.bat`, que verifica dependencias, inicia MariaDB, aplica migraciones y carga los datos sin duplicarlos.

La barra superior incluye el botón **Administración**. En una base nueva, el comando de poblamiento crea este acceso local:

- Usuario: `admin`
- Contraseña: `jarax`

Estas credenciales son solo para desarrollo. Modifica `ADMIN_USERNAME`, `ADMIN_PASSWORD` y `ADMIN_EMAIL` en `.env` antes de publicar la aplicación.

## Módulos

- `/` — catálogo de 40 productos obtenidos desde la base activa.
- `/panel/` — indicadores generales.
- `/punto-de-venta/` — venta real en base de datos y descuento transaccional de stock.
- `/ventas/` — ingresos, costos y margen.
- `/logistica/` — bodegas, compras, movimientos y alertas.
- `/personas/` — empleados, cargos, contratos y nómina.
- `/produccion/` — recetas, órdenes y consumos.
- `/finanzas/` — ingresos, costos, gastos y resultado.
- `/api/productos/` — API JSON derivada del esquema normalizado.
- `/configuracion/` — motor, versión, base activa y accesos.
- `/admin/` — CRUD completo de todas las entidades.

## ES3: CRUD, reportes y clientes

- `/productos/nuevo/` — crear productos desde el sitio.
- `/productos/<id>/editar/` — editar productos, precio y stock desde el sitio.
- `/productos/<id>/eliminar/` — retirar productos con confirmación y borrado lógico.
- `/reportes/categorias/` — reporte agrupado con `Count`, `Avg` y `Sum` del ORM.
- `/reportes/stock-critico/` — reporte filtrado y ordenado de stock bajo.
- `/consultas/` — formulario `ModelForm` de clientes con validaciones y CSRF.

La ficha de producto conserva los últimos tres productos visitados en la sesión del navegador.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test catalogo
```

El comando `poblar_crisferreterias` es idempotente. Carga 40 productos, precios, inventario por bodega, proveedores, compras, ventas, clientes, personal, nómina, producción, despachos y transacciones financieras.

El archivo `uso_ia.md` registra las consultas y ajustes realizados con IA. La Parte 2 debe completarla personalmente el estudiante, tal como exige la pauta.
