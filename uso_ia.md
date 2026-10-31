# Uso de IA - Evaluación Sumativa 2

## Parte 1 - Registro de consultas

### Consulta 1 - Modelo
Se solicitó ayuda para transformar el catálogo de CrisSteel de una lista de productos escrita en la vista a un modelo Django llamado `Producto`, manteniendo los campos requeridos por la evaluación.

### Consulta 2 - Poblamiento
**Prompt:** "Genera un poblamiento inicial de 40 productos de ferretería chilenos realistas para Django, con categorías, precios e inventario, listo para cargar mediante un comando ORM."

**Resumen de la respuesta:** se propuso un conjunto de datos distribuido entre categorías de ferretería y relacionado con precios, bodegas y movimientos de inventario.

**Uso y ajustes:** los datos se integraron en el comando idempotente `poblar_crisferreterias`, adaptándolos al esquema normalizado de MariaDB, donde el precio vigente y el stock se calculan desde entidades relacionadas.

### Consulta 3 - Integración con la interfaz
Se solicitó adaptar las vistas para que el catálogo, el detalle y el punto de venta consultaran `Producto.objects` sin cambiar el diseño visual de CrisSteel.

### Consulta 4 - Ruta principal y ejecución local
**Prompt:** "Haz que la página de la ferretería se abra en `http://127.0.0.1:8000/`, que ese enlace aparezca al ejecutar `python manage.py runserver` y que el proyecto cumpla lo solicitado en la pauta ES2."

**Resumen de la respuesta:** se revisaron la ruta raíz, el comando de desarrollo, los iniciadores y la documentación para dejar un único acceso local coherente.

**Uso y ajustes:** se confirmó que el catálogo se sirve desde `/`, se fijó el puerto predeterminado en 8000, se agregó un mensaje visible con la URL al iniciar Django y se actualizaron los archivos de ejecución y documentación.

### Consulta 5 - Diseño visual de referencia y ZIP portátil
**Prompt:** "Modifica el ZIP para que la página se vea como las imágenes de referencia y después actualiza el repositorio de GitHub con lo realizado."

**Resumen de la respuesta:** se reutilizó la interfaz modular de CrisSteel mostrada en las capturas: encabezado, navegación, héroes oscuros, fondo cuadriculado, tarjetas de indicadores, tablas, catálogo visual, punto de venta y pie de página. Para que la misma interfaz pudiera abrirse sin instalar un servidor de base de datos, se añadió un modo SQLite local sin quitar la configuración MariaDB de la evaluación.

**Uso y ajustes:** se incorporó detección del motor activo, etiquetas coherentes en pantalla, una vista de configuración compatible con ambos motores y el iniciador `iniciar_portatil.bat`. También se preparó una base local con los datos integrales y el superusuario solicitado, y se verificaron las rutas principales en escritorio y móvil. El propio `manage.py` muestra el enlace antes de cargar Django; el comando `runserver` vuelve a mostrarlo cuando el puerto queda activo y lo abre automáticamente en el navegador. También se añadió el acceso directo `ABRIR_CRISSTEEL.url`.

### Consulta 6 - El enlace aparece pero la página no abre
**Prompt:** "Ahora está el link, pero no puedo acceder a la página que hiciste."

**Resumen de la respuesta:** se comprobó que no había ningún servidor escuchando en el puerto 8000. La ejecución terminaba porque el modo SQLite intentaba importar innecesariamente `PyMySQL` y porque la instalación local de Django 5.0 requería la sintaxis compatible de `CheckConstraint`.

**Uso y ajustes:** la integración de `PyMySQL` se movió a la configuración exclusiva de MariaDB y la restricción del inventario se hizo compatible con Django 5.0 y 5.2. Luego se ejecutó `python manage.py runserver` con el Python instalado en el equipo y se verificó que la portada respondiera correctamente en `http://127.0.0.1:8000/`.

### Ajustes realizados
Se mantuvieron las imágenes y plantillas de la ES1. Se agregó el modelo, la migración, el registro en Admin, la fixture `productos.json` y las consultas ORM. También se ajustó el stock que superaba el máximo solicitado por la pauta.

## Parte 2 - Explicación personal

**Esta sección debe ser escrita por el estudiante con sus propias palabras antes de entregar.**

Explica en 10 a 20 líneas qué le pediste a la IA, qué parte utilizaste, qué tuviste que corregir y qué aprendiste al pasar el catálogo desde datos estáticos a una base de datos.

Durante la puesta en marcha de CrisSteel, revisé cómo se persistían/guardaban los datos del catálogo, los precios, el inventario y las ventas. El README identifica MariaDB 10.4.32, incluida en XAMPP, como servidor de base de datos. En `config/settings.py`, Django carga variables desde `.env` y configura `DATABASES["default"]` con el nombre `CrisFerreterias`, el host `127.0.0.1` y el puerto `3306`. El uso de una dirección de loopback sitúa la conexión en el mismo equipo que ejecuta la aplicación.

¿Por qué aparece `django.db.backends.mysql` si el servidor es MariaDB? Django utiliza ese backend para ambos motores. El valor de `ENGINE` selecciona la capa del framework que traduce operaciones del ORM a SQL y gestiona cursores y conexiones. En `requirements.txt`, el proyecto fija PyMySQL 1.1.2. Esta biblioteca cliente implementa la interfaz DB-API 2.0 de Python para comunicarse con servidores MySQL y MariaDB. La instrucción `pymysql.install_as_MySQLdb()` registra PyMySQL con el nombre de módulo que espera el backend. En esta arquitectura, PyMySQL cumple la función de driver; el backend de Django integra el driver con el ORM; MariaDB recibe y ejecuta las consultas.

¿Qué ocurre cuando una vista consulta un producto? El ORM construye la operación a partir del modelo o del `QuerySet`. El backend la convierte al dialecto correspondiente y solicita un cursor al driver. PyMySQL establece la conexión con el servidor en el host y puerto configurados, transmite la consulta y devuelve las filas resultantes. Django transforma esas filas en objetos del modelo. En la configuración también se declara `utf8mb4`, se activa `STRICT_TRANS_TABLES` mediante `init_command` y se fija `CONN_MAX_AGE=60`, que permite reutilizar conexiones hasta su edad máxima configurada.

La persistencia se observa en las operaciones del sistema. El README describe un punto de venta que registra ventas y descuenta inventario de forma transaccional. En términos de base de datos, la operación debe mantener relacionados el registro de la venta y la actualización del stock: si ocurre un error, corresponde comprobar que la transacción revierta los cambios incompletos. El repositorio también configura una base de prueba separada, `CrisFerreterias_test`, y documenta comandos de comprobación y pruebas para la aplicación.

¿Qué queda por revisar como ejecutor? La configuración conserva `DEBUG=True`, una clave de desarrollo y valores de respaldo para la conexión. Sirve para poner en marcha el entorno local; antes de desplegarlo, revisaría esas opciones, trasladaría los secretos a variables de entorno y configuraría el entorno de producción. También evaluaría `CONN_MAX_AGE=60` según el servidor utilizado: la documentación de Django señala que el servidor de desarrollo crea un hilo por petición, por lo que las conexiones persistentes requieren una revisión específica en ese escenario.

Al describir esta integración, distingo el backend del framework, el driver cliente y el servidor MariaDB porque cada uno interviene en una etapa distinta de la consulta. Esa separación permite diagnosticar con más precisión errores de configuración, autenticación, disponibilidad del servicio o ejecución SQL.
