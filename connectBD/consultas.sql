-- CrisSteel · CrisFerreterias: consultas operacionales y analiticas centralizadas (MariaDB).
-- La aplicacion escribe y consulta mediante el ORM de Django. Este archivo concentra
-- equivalentes SQL para auditoria, soporte y análisis en clientes MariaDB.
-- Los parametros con prefijo : deben ser reemplazados por el cliente SQL.

-- 1. Catalogo normalizado: producto, clasificaciones, precio vigente y stock derivado.
SELECT p.id,
       p.sku,
       p.nombre,
       c.nombre AS categoria,
       m.nombre AS marca,
       u.simbolo AS unidad,
       COALESCE((
           SELECT pp.monto
           FROM catalogo_precioproducto pp
           INNER JOIN catalogo_listaprecio lp ON lp.id = pp.lista_id
           WHERE pp.producto_id = p.id
             AND lp.activa = 1
             AND pp.vigente_desde <= CURDATE()
             AND (pp.vigente_hasta IS NULL OR pp.vigente_hasta >= CURDATE())
           ORDER BY pp.vigente_desde DESC, pp.id DESC
           LIMIT 1
       ), 0) AS precio_vigente,
       COALESCE(SUM(mi.cantidad), 0) AS stock_total,
       p.punto_reorden,
       p.activo
FROM catalogo_producto p
INNER JOIN catalogo_categoria c ON c.id = p.categoria_id
INNER JOIN catalogo_unidadmedida u ON u.id = p.unidad_id
LEFT JOIN catalogo_marca m ON m.id = p.marca_id
LEFT JOIN catalogo_movimientoinventario mi ON mi.producto_id = p.id
GROUP BY p.id, p.sku, p.nombre, c.nombre, m.nombre, u.simbolo,
         p.punto_reorden, p.activo
ORDER BY p.nombre;

-- 2. Busqueda de catalogo. Ejemplo: :termino = 'taladro'.
SELECT p.sku, p.nombre, c.nombre AS categoria, m.nombre AS marca
FROM catalogo_producto p
INNER JOIN catalogo_categoria c ON c.id = p.categoria_id
LEFT JOIN catalogo_marca m ON m.id = p.marca_id
WHERE p.nombre LIKE CONCAT('%', :termino, '%')
   OR p.sku LIKE CONCAT('%', :termino, '%')
   OR p.descripcion LIKE CONCAT('%', :termino, '%')
   OR m.nombre LIKE CONCAT('%', :termino, '%')
ORDER BY p.nombre;

-- 3. Stock por producto y bodega: no existe una columna de stock duplicada.
SELECT b.codigo,
       b.nombre AS bodega,
       p.sku,
       p.nombre AS producto,
       u.simbolo AS unidad,
       SUM(mi.cantidad) AS stock
FROM catalogo_movimientoinventario mi
INNER JOIN catalogo_producto p ON p.id = mi.producto_id
INNER JOIN catalogo_bodega b ON b.id = mi.bodega_id
INNER JOIN catalogo_unidadmedida u ON u.id = p.unidad_id
GROUP BY b.id, b.codigo, b.nombre, p.id, p.sku, p.nombre, u.simbolo
ORDER BY b.codigo, p.nombre;

-- 4. Productos bajo el punto de reposicion.
SELECT p.sku,
       p.nombre,
       c.nombre AS categoria,
       COALESCE(SUM(mi.cantidad), 0) AS stock,
       p.punto_reorden
FROM catalogo_producto p
INNER JOIN catalogo_categoria c ON c.id = p.categoria_id
LEFT JOIN catalogo_movimientoinventario mi ON mi.producto_id = p.id
WHERE p.activo = 1
GROUP BY p.id, p.sku, p.nombre, c.nombre, p.punto_reorden
HAVING COALESCE(SUM(mi.cantidad), 0) <= p.punto_reorden
ORDER BY stock, p.nombre;

-- 5. Historial de precios por lista.
SELECT p.sku,
       p.nombre AS producto,
       lp.nombre AS lista,
       lp.moneda,
       pp.monto,
       pp.vigente_desde,
       pp.vigente_hasta
FROM catalogo_precioproducto pp
INNER JOIN catalogo_producto p ON p.id = pp.producto_id
INNER JOIN catalogo_listaprecio lp ON lp.id = pp.lista_id
ORDER BY p.nombre, lp.nombre, pp.vigente_desde DESC;

-- 6. Proveedores posibles por producto.
SELECT p.sku,
       p.nombre AS producto,
       pr.rut,
       pr.razon_social,
       pp.codigo_proveedor,
       pp.plazo_entrega_dias,
       pp.costo_ultimo,
       pp.preferente
FROM catalogo_productoproveedor pp
INNER JOIN catalogo_producto p ON p.id = pp.producto_id
INNER JOIN catalogo_proveedor pr ON pr.id = pp.proveedor_id
ORDER BY p.nombre, pp.preferente DESC, pp.costo_ultimo;

-- 7. Ventas, costo y margen por documento.
SELECT v.numero,
       v.fecha AS fecha,
       cl.nombre AS cliente,
       v.estado,
       ROUND(SUM(dv.cantidad * dv.precio_unitario) - v.descuento, 2) AS ingreso,
       ROUND(SUM(dv.cantidad * dv.costo_unitario), 2) AS costo,
       ROUND(SUM(dv.cantidad * (dv.precio_unitario - dv.costo_unitario)) - v.descuento, 2) AS margen
FROM catalogo_venta v
INNER JOIN catalogo_cliente cl ON cl.id = v.cliente_id
INNER JOIN catalogo_detalleventa dv ON dv.venta_id = v.id
WHERE v.estado <> 'ANULADA'
GROUP BY v.id, v.numero, v.fecha, cl.nombre, v.estado, v.descuento
ORDER BY v.fecha DESC;

-- 8. Resumen mensual de ventas.
SELECT periodo,
       COUNT(*) AS ventas,
       ROUND(SUM(ingreso), 2) AS ingresos_brutos,
       ROUND(SUM(costo), 2) AS costo_mercaderia,
       ROUND(SUM(ingreso - costo), 2) AS margen_bruto
FROM (
    SELECT v.id,
           DATE_FORMAT(v.fecha, '%Y-%m') AS periodo,
           SUM(dv.cantidad * dv.precio_unitario) - v.descuento AS ingreso,
           SUM(dv.cantidad * dv.costo_unitario) AS costo
    FROM catalogo_venta v
    INNER JOIN catalogo_detalleventa dv ON dv.venta_id = v.id
    WHERE v.estado <> 'ANULADA'
    GROUP BY v.id, DATE_FORMAT(v.fecha, '%Y-%m'), v.descuento
) AS ventas_por_documento
GROUP BY periodo
ORDER BY periodo DESC;

-- 9. Compras recibidas y costo total.
SELECT co.numero,
       co.fecha,
       pr.razon_social AS proveedor,
       b.nombre AS bodega,
       co.estado,
       ROUND(SUM(dc.cantidad * dc.costo_unitario), 2) AS total
FROM catalogo_compra co
INNER JOIN catalogo_proveedor pr ON pr.id = co.proveedor_id
INNER JOIN catalogo_bodega b ON b.id = co.bodega_id
INNER JOIN catalogo_detallecompra dc ON dc.compra_id = co.id
GROUP BY co.id, co.numero, co.fecha, pr.razon_social, b.nombre, co.estado
ORDER BY co.fecha DESC;

-- 10. Contrato vigente y costo mensual de personal.
SELECT e.rut,
       CONCAT(e.nombres, ' ', e.apellidos) AS empleado,
       d.nombre AS departamento,
       ca.nombre AS cargo,
       ct.sueldo_base,
       ct.horas_semanales,
       ct.fecha_inicio
FROM catalogo_contratolaboral ct
INNER JOIN catalogo_empleado e ON e.id = ct.empleado_id
INNER JOIN catalogo_cargo ca ON ca.id = ct.cargo_id
INNER JOIN catalogo_departamento d ON d.id = ca.departamento_id
WHERE e.activo = 1
  AND ct.fecha_inicio <= CURDATE()
  AND (ct.fecha_fin IS NULL OR ct.fecha_fin >= CURDATE())
ORDER BY d.nombre, e.apellidos;

-- 11. Nomina por periodo y departamento.
SELECT pn.nombre AS periodo,
       d.nombre AS departamento,
       COUNT(ls.id) AS liquidaciones,
       SUM(ls.total_haberes) AS total_haberes,
       SUM(ls.total_descuentos) AS total_descuentos,
       SUM(ls.liquido) AS total_liquido
FROM catalogo_liquidacionsueldo ls
INNER JOIN catalogo_periodonomina pn ON pn.id = ls.periodo_id
INNER JOIN catalogo_contratolaboral ct ON ct.id = ls.contrato_id
INNER JOIN catalogo_cargo ca ON ca.id = ct.cargo_id
INNER JOIN catalogo_departamento d ON d.id = ca.departamento_id
GROUP BY pn.id, pn.nombre, d.id, d.nombre
ORDER BY pn.fecha_inicio DESC, d.nombre;

-- 12. Requerimientos y costo estandar de recetas de produccion.
SELECT r.codigo,
       r.version,
       pt.sku AS producto_terminado,
       pt.nombre AS producto,
       pc.sku AS componente_sku,
       pc.nombre AS componente,
       cr.cantidad AS cantidad_por_receta,
       COALESCE((
           SELECT ppr.costo_ultimo
           FROM catalogo_productoproveedor ppr
           WHERE ppr.producto_id = pc.id
           ORDER BY ppr.preferente DESC, ppr.costo_ultimo
           LIMIT 1
       ), 0) AS costo_unitario_referencia,
       ROUND(cr.cantidad * COALESCE((
           SELECT ppr.costo_ultimo
           FROM catalogo_productoproveedor ppr
           WHERE ppr.producto_id = pc.id
           ORDER BY ppr.preferente DESC, ppr.costo_ultimo
           LIMIT 1
       ), 0), 2) AS costo_componente
FROM catalogo_componentereceta cr
INNER JOIN catalogo_recetaproduccion r ON r.id = cr.receta_id
INNER JOIN catalogo_producto pt ON pt.id = r.producto_terminado_id
INNER JOIN catalogo_producto pc ON pc.id = cr.componente_id
WHERE r.activa = 1
ORDER BY r.codigo, r.version, pc.nombre;

-- 13. Avance y costo real de ordenes de produccion.
SELECT op.numero,
       pt.nombre AS producto_terminado,
       b.nombre AS bodega,
       op.estado,
       op.cantidad_planificada,
       op.cantidad_producida,
       ROUND(COALESCE(SUM(cp.cantidad * cp.costo_unitario), 0), 2) AS costo_consumido
FROM catalogo_ordenproduccion op
INNER JOIN catalogo_recetaproduccion r ON r.id = op.receta_id
INNER JOIN catalogo_producto pt ON pt.id = r.producto_terminado_id
INNER JOIN catalogo_bodega b ON b.id = op.bodega_id
LEFT JOIN catalogo_consumoproduccion cp ON cp.orden_id = op.id
GROUP BY op.id, op.numero, pt.nombre, b.nombre, op.estado,
         op.cantidad_planificada, op.cantidad_producida
ORDER BY op.fecha_inicio DESC;

-- 14. Estado de resultados por centro de costo.
SELECT cc.codigo,
       cc.nombre AS centro_costo,
       ROUND(SUM(CASE WHEN cf.tipo = 'INGRESO' THEN tf.monto ELSE 0 END), 2) AS ingresos,
       ROUND(SUM(CASE WHEN cf.tipo = 'COSTO' THEN tf.monto ELSE 0 END), 2) AS costos,
       ROUND(SUM(CASE WHEN cf.tipo = 'GASTO' THEN tf.monto ELSE 0 END), 2) AS gastos,
       ROUND(SUM(CASE
           WHEN cf.tipo = 'INGRESO' THEN tf.monto
           WHEN cf.tipo IN ('COSTO', 'GASTO') THEN -tf.monto
           ELSE 0
       END), 2) AS resultado
FROM catalogo_transaccionfinanciera tf
INNER JOIN catalogo_categoriafinanciera cf ON cf.id = tf.categoria_id
INNER JOIN catalogo_centrocosto cc ON cc.id = tf.centro_costo_id
GROUP BY cc.id, cc.codigo, cc.nombre
ORDER BY cc.codigo;

-- 15. Trazabilidad de despachos y ventas incluidas.
SELECT d.numero AS despacho,
       d.estado,
       d.fecha,
       t.nombre AS transportista,
       t.patente,
       v.numero AS venta,
       cl.nombre AS cliente,
       d.costo
FROM catalogo_despachoventa dv
INNER JOIN catalogo_despacho d ON d.id = dv.despacho_id
INNER JOIN catalogo_transportista t ON t.id = d.transportista_id
INNER JOIN catalogo_venta v ON v.id = dv.venta_id
INNER JOIN catalogo_cliente cl ON cl.id = v.cliente_id
ORDER BY d.fecha DESC, v.numero;
