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
