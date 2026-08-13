# Producto V1

## Objetivo

Prep Personal es una app Android offline para usuarios con ingresos variables que necesitan decidir cuanto pueden usar hoy sin comprometer obligaciones, ahorro, inversion o deuda.

## Principios del producto

1. El dinero disponible no es igual al saldo total.
2. La quincena es una unidad de planeacion central.
3. Las sugerencias deben ser explicables y auditables.
4. El ingreso fijo mensual esperado es una base editable, no una garantia.
5. La app debe funcionar sin internet.

## Alcance funcional V1

### 1. Ingresos

- Registrar ingresos manuales.
- Clasificar ingresos por tipo y cartera.
- Configurar ingresos fijos mensuales esperados.
- Editar montos esperados si suben o bajan.
- Comparar ingreso esperado vs. ingreso reportado real.

### 2. Gastos

- Registrar gastos por categoria.
- Soportar categorias fijas, variables y de nomina.
- Permitir tags reutilizables.

### 3. Carteras

- Efectivo.
- Banco.
- Cooperativa.
- Otras carteras futuras.

### 4. Obligaciones

- Modelar casa, luz, agua, Netflix, colegio, nomina y manutencion como obligaciones programadas.
- Guardar monto, frecuencia, fecha de vencimiento y estado de cobertura.

### 5. Presupuestos

- Buckets base: obligaciones fijas, personal, ahorro-inversion-deuda.
- Presupuesto por categoria.
- Seguimiento mensual y por quincena.

### 6. Insights

- Alertas por categorias con desvio de tendencia.
- Recomendaciones de ajuste a ahorro o gasto personal.
- Advertencias si una transaccion rompe reserva de quincena.

## Regla financiera de la app

La app no aplica un 50, 30, 20 fijo a cada ingreso. Usa este orden:

1. Reservar obligaciones proximas y criticas.
2. Reservar metas minimas de ahorro, inversion y deuda.
3. Evaluar ingreso fijo mensual esperado contra ingreso real reportado.
4. Liberar solo el remanente como disponible personal.

## Home principal

La pregunta que responde la home es:

Cuanto puedo usar hoy sin poner en riesgo mi quincena.

## Fuera de alcance en esta fase

- Sincronizacion en nube.
- Conexion bancaria.
- Machine learning avanzado.
- Multiusuario.