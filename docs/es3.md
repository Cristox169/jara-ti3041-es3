# Evaluación ES3 implementada

Esta versión parte del catálogo CrisSteel de ES2 y agrega las funciones solicitadas por la guía `TI3041_ES3_Evaluacion_U2_con_IA.pdf`.

## Entregables técnicos

1. CRUD web de `Producto`: crear, editar y retirar desde el catálogo. El precio se persiste en `PrecioProducto` y el stock se registra mediante movimientos de inventario.
2. Reporte ORM agrupado por categoría: cantidad de productos, stock total y precio promedio.
3. Reporte ORM de stock crítico: filtro por punto de reorden o por límite recibido en la URL.
4. `ConsultaCliente`: modelo, migración, registro en Admin, `ModelForm`, validaciones, CSRF y confirmación.
5. Sesiones: la ficha guarda los últimos tres productos visitados en `request.session`.

## Rutas principales

- `/productos/nuevo/`
- `/productos/<id>/editar/`
- `/productos/<id>/eliminar/`
- `/reportes/categorias/`
- `/reportes/stock-critico/`
- `/consultas/`

La Parte 2 de `uso_ia.md` debe ser revisada y redactada por el estudiante con sus propias palabras antes de la entrega.

## Verificación solicitada por la pauta

Se ejecutó `python manage.py test catalogo --verbosity 1` sobre una base de pruebas aislada. Las comprobaciones incluyen:

- formulario de clientes con correo inválido, nombre/mensaje demasiado cortos y campos vacíos; la vista conserva el formulario y muestra mensajes claros sin guardar registros inválidos;
- reporte por categorías comparado con agregaciones ORM de la base y con el contador de productos del changelist de `/admin/`;
- reporte de stock crítico comparado con la suma de movimientos, considerando stock `0` cuando un producto no tiene movimientos;
- ciclo web completo de producto: crear, editar y retirar mediante POST, con redirección al listado y reflejo de los cambios en la base.

Resultado original: 12 pruebas ejecutadas correctamente; con la ampliación de autenticación y documentos, la suite actual alcanza 14 pruebas correctas.

## Ampliación CrisFerreterias

La versión posterior incorpora autenticación obligatoria, caducidad por siete minutos de inactividad, navegación agrupada por ventas y apps administrativas, campos de stock mínimo/ideal y brecha de reposición. También se agregaron carro de compra, cotizaciones, órdenes de trabajo, notas de crédito y un dashboard con carrusel de insights y filtros de abastecimiento.
