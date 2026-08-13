# Arquitectura V1

## Stack base

- Flutter para cliente Android.
- Material 3 con tema custom premium light.
- SQLite local con sqflite.
- Estructura modular por features.

## Decisiones actuales

1. Se adopto SQLite local con tablas simples para no retrasar la primera APK offline.
2. El controlador de estado centraliza datos y reglas financieras iniciales.
3. La UI ya esta separada por features para evitar reescritura cuando entre el dominio real.

## Estructura

```text
lib/
  main.dart
  src/
    app.dart
    core/
      theme/
      ui/
      utils/
    data/
    domain/
    features/
      home/
      transactions/
      plan/
      insights/
      settings/
    state/
docs/
  producto-v1.md
  arquitectura-v1.md
```

## Dominio que debe consolidarse en la siguiente fase

### Entidades base

- Wallet
- IncomeSource
- IncomeTransaction
- ExpenseTransaction
- Obligation
- BudgetBucket
- Category
- Tag
- Insight

### Servicios de dominio

- IncomeAllocationService
- QuincenaPlanner
- BudgetHealthService
- InsightEngine

## Persistencia actual

- Tablas SQLite: fixed_income_sources, obligations, transactions.
- Seeder inicial para que la app arranque con un escenario realista.
- Siguiente mejora recomendada: migrar a Drift si se quiere tipado fuerte y consultas mas complejas.

## Estado actual y siguiente paso

- AppController con ChangeNotifier para mover rapido el MVP.
- Siguiente mejora recomendada: migrar a Riverpod cuando el dominio crezca y entren mas casos de uso.

## Regla critica a probar

Cuando entra un ingreso:

1. revisar obligaciones pendientes hasta la proxima quincena,
2. revisar metas minimas configuradas,
3. revisar ingreso fijo esperado vs. ingreso real,
4. calcular disponible personal autentico,
5. emitir advertencias o recomendaciones.

## Android

- Proyecto inicializado solo con plataforma Android.
- Siguiente ajuste recomendado: cambiar icono, splash y firma release.