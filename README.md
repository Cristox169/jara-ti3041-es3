# CrisSteel · CrisFerreterias

Sistema Django integral para una ferretería, construido sobre el proyecto ES2 original y conectado a MariaDB mediante XAMPP. Cubre catálogo, punto de venta persistente, compras, inventario, logística, recursos humanos, nómina, producción y análisis financiero. La aplicación no usa SQLite: toda la información visible se consulta desde la base `CrisFerreterias`.

## Inicio rápido con XAMPP

En Windows, ejecuta `iniciar_crissteel.bat`. El iniciador crea el entorno virtual, instala las dependencias, inicia MariaDB de XAMPP, crea la base y el usuario, aplica las migraciones, carga los datos y abre automáticamente:

- Sitio: <http://127.0.0.1:8000/>
- Administración: <http://127.0.0.1:8000/admin/>

También se puede preparar e iniciar manualmente:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\preparar_xampp.ps1
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py poblar_crisferreterias
.\.venv\Scripts\python.exe manage.py runserver
```

Al ejecutar `python manage.py runserver`, Django muestra el enlace <http://127.0.0.1:8000/> únicamente después de conectarse a XAMPP y activar el servidor. En Windows, la página también se abre automáticamente. El archivo `ABRIR_CRISSTEEL.url` permite volver a abrirla con doble clic mientras el servidor siga ejecutándose. Usa `python manage.py runserver --no-browser` si no deseas abrir el navegador.

## Base de datos MariaDB de XAMPP

- Motor comprobado: MariaDB 10.4.32 incluido en XAMPP.
- Base: `CrisFerreterias`.
- Servidor: `127.0.0.1:3306`.
- Usuario de la aplicación: `crisferreterias_app`.
- Juego de caracteres: `utf8mb4`.
- Configuración privada: `.env` (ignorada por Git).
- Esquema normalizado: [`docs/normalizacion_5fn.md`](docs/normalizacion_5fn.md).
- Consultas analíticas: [`connectBD/consultas.sql`](connectBD/consultas.sql).

`Producto` no almacena precio ni stock. El precio vigente se obtiene desde `PrecioProducto` y el inventario se deriva de `MovimientoInventario`. Las imágenes Base64 están almacenadas en `Producto.imagen_base64`. Las relaciones multivaluadas están descompuestas mediante tablas puente y los documentos usan cabecera/detalle.

## Preparación de XAMPP

Desde la carpeta del proyecto:

```powershell
.\scripts\preparar_xampp.ps1
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py poblar_crisferreterias
.\.venv\Scripts\python.exe manage.py runserver
```

El script usa `C:\xampp` y la clave local de `root` configurada en XAMPP. Puedes cambiarla mediante la variable `XAMPP_ROOT_PASSWORD`. El SQL reproducible está en `crear_bd_xampp.sql`.

La barra superior incluye el botón **Administración**. En una base nueva, el comando de poblamiento crea este acceso local:

- Usuario: `admin`
- Contraseña: `jarax`

Estas credenciales son solo para desarrollo. Modifica `ADMIN_USERNAME`, `ADMIN_PASSWORD` y `ADMIN_EMAIL` en `.env` antes de publicar la aplicación.

## Módulos

- `/` — catálogo de 40 productos e imágenes obtenidos desde MariaDB.
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

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test catalogo
```

El comando `poblar_crisferreterias` es idempotente. Carga 40 productos, precios, inventario por bodega, proveedores, compras, ventas, clientes, personal, nómina, producción, despachos y transacciones financieras.

El archivo `uso_ia.md` registra las consultas y ajustes realizados con IA. La Parte 2 debe completarla personalmente el estudiante, tal como exige la pauta.
