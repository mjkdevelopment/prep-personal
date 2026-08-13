# Prep Personal

Aplicacion Android offline para manejo de gastos personales, ingresos variables y planeacion por quincena.

## Estado actual

Este repositorio ya incluye:

- Base Flutter orientada a Android.
- Shell inicial del MVP con navegacion inferior.
- Pantallas iniciales para Inicio, Transacciones, Plan, Insights y Ajustes.
- Persistencia local real con SQLite para ingresos fijos, obligaciones y transacciones.
- Formularios funcionales para registrar transacciones y editar ingresos fijos mensuales.
- Motor inicial de asignacion por ingreso segun obligaciones, metas e ingreso esperado.
- Documentacion funcional y tecnica en la carpeta docs.

## Enfoque del producto

Prep Personal no trata el 50, 30, 20 como regla fija. Lo usa como objetivo adaptable. El motor real prioriza:

1. Obligaciones fijas y fechas de vencimiento.
2. Metas de ahorro, inversion y deuda.
3. Disponible personal autentico segun ingreso reportado y reserva de quincena.

## Estructura inicial

- lib/src/app.dart: shell principal de la aplicacion.
- lib/src/core: tema, widgets base y utilidades.
- lib/src/features: pantallas funcionales del MVP.
- lib/src/mock: datos semilla para prototipado del dominio.
- docs: especificacion funcional y arquitectura v1.

## Comandos utiles

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

## Siguiente fase recomendada

1. Incorporar persistencia local con Drift o SQLite tipado.
2. Reemplazar categorias y obligaciones semilla por CRUD completo.
3. Refinar el motor financiero con pruebas unitarias mas exhaustivas.
4. Integrar exportacion e importacion de respaldos offline.
