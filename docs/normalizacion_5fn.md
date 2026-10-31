# Diseño de base de datos MariaDB en quinta forma normal

## Objetivo

La base de datos MariaDB soporta catálogo, ventas, abastecimiento, inventario, despachos, recursos humanos, producción y análisis financiero sin guardar el mismo hecho en más de una tabla. Los valores calculables, como stock, total de una venta, costo de una compra y margen, se obtienen desde relaciones base mediante ORM o SQL.

## Criterios aplicados

- Cada tabla representa un solo tipo de hecho y posee una clave primaria.
- Los atributos dependen de la clave completa y no de una parte de ella.
- Las categorías, marcas, unidades, bodegas, cargos, métodos de pago y centros de costo se almacenan como datos maestros independientes.
- Las relaciones muchos a muchos se resuelven con tablas puente: `ProductoProveedor`, `DespachoVenta`, `ComponenteReceta` y `AsignacionTurno`.
- Las ventas y compras separan cabecera y detalle; cada línea depende de su documento y producto.
- El precio se mantiene como histórico en `PrecioProducto`. No existe una columna precio en `Producto`.
- El stock se calcula sumando `MovimientoInventario`. No existe una columna stock en `Producto`.
- Los contratos y listas de precio son temporales, lo que evita sobrescribir hechos históricos.
- Las recetas de producción están versionadas y sus componentes se guardan como relaciones independientes.
- Los hechos financieros se clasifican por categoría y centro de costo, permitiendo analizar ingresos, costos y gastos sin columnas repetidas.

## Relaciones sin pérdida

Las descomposiciones se pueden recomponer mediante claves foráneas sin generar tuplas espurias. Por ejemplo, la relación entre productos y proveedores se reconstruye desde `Producto`, `Proveedor` y `ProductoProveedor`; un despacho con varias ventas se reconstruye desde `Despacho`, `Venta` y `DespachoVenta`; y una receta con varios componentes se reconstruye desde `RecetaProduccion`, `Producto` y `ComponenteReceta`.

Estas tablas puente contienen únicamente atributos que dependen de la relación completa. Por esta razón las dependencias de unión quedan representadas explícitamente y el esquema satisface el objetivo práctico de quinta forma normal para el alcance del proyecto.

## Dominios funcionales

| Área | Tablas principales | Información derivada |
|---|---|---|
| Catálogo | Categoria, Marca, UnidadMedida, Producto, ListaPrecio, PrecioProducto | Precio vigente |
| Logística | Bodega, MovimientoInventario, Proveedor, ProductoProveedor, Compra, DetalleCompra, Despacho | Stock por producto y bodega |
| Ventas | Cliente, Venta, DetalleVenta, MetodoPago, PagoVenta | Total, costo y margen |
| Recursos humanos | Departamento, Cargo, Empleado, ContratoLaboral, Turno, AsignacionTurno | Dotación y nómina base |
| Producción | RecetaProduccion, ComponenteReceta, OrdenProduccion, ConsumoProduccion | Costo de materiales y avance |
| Finanzas | CategoriaFinanciera, CentroCosto, TransaccionFinanciera | Resultado por naturaleza y centro |


