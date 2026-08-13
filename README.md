# Gride Ledger

Aplicacion web para manejo de ingresos, gastos, obligaciones y reserva por quincena. La APK queda en pausa: el producto principal ahora es web, con backend en Python y frontend React, desplegable en Railway.

## Stack actual

- Backend: FastAPI + SQLite.
- Frontend: React + Vite + TypeScript.
- Deploy: Railway con un solo Dockerfile.

## Regla financiera conservada

1. Reservar obligaciones proximas y criticas.
2. Reservar metas minimas de ahorro, inversion y deuda.
3. Comparar ingreso esperado contra ingreso real reportado.
4. Liberar solo el remanente como disponible personal.

## Estructura

- backend/: API, persistencia y calculos financieros.
- backend/tests/: pruebas base del backend.
- frontend/: SPA con dashboard, formularios e historial editable.
- docs/: documentacion funcional heredada.
- lib/: implementacion Flutter anterior, retenida solo como referencia del dominio.

## Desarrollo local

### Backend

```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend usa `/api` como base. En produccion FastAPI sirve `frontend/dist` para publicar API y SPA desde el mismo proceso.

## Validacion

### Backend

```bash
python -m pytest backend/tests -q
```

### Frontend

```bash
cd frontend
npm run build
```

## Deploy en Railway

1. Conectar el repositorio a Railway.
2. Dejar que Railway use el Dockerfile de la raiz.
3. Crear un volumen persistente y montarlo en `/data`.
4. Configurar estas variables de entorno en Railway antes del primer deploy:
	- `APP_DB_PATH=/data/gride_ledger.db`
	- `OWNER_BOOTSTRAP_USERNAME=<tu usuario owner inicial>`
	- `OWNER_BOOTSTRAP_PASSWORD=<tu contrasena owner inicial>`
	- `OWNER_BOOTSTRAP_THEME_ID=emerald_editorial` opcional
	- `REQUIRE_EXISTING_DB=1` opcional despues del primer deploy estable, para impedir que el servicio arranque sobre una base nueva o un volumen vacio por error
5. El primer arranque creara automaticamente la cuenta owner solo si todavia no existe una cuenta owner en la base.
6. El build instalara dependencias del frontend, generara `frontend/dist`, instalara el backend Python y publicara FastAPI en el puerto asignado.
7. La SPA y la API quedaran servidas desde el mismo contenedor.
8. En Railway el bootstrap manual por codigo local queda deshabilitado por defecto. Si no existe owner, la cuenta inicial debe entrar por `OWNER_BOOTSTRAP_USERNAME` y `OWNER_BOOTSTRAP_PASSWORD` o por la restauracion del volumen persistente correcto.

### Bootstrap automatico owner

- El bootstrap por variables de entorno ocurre una sola vez: cuando no existe ningun usuario `owner`.
- Si luego haces redeploy con las mismas variables, la app no recrea ni pisa la cuenta owner.
- Si `OWNER_BOOTSTRAP_USERNAME` coincide con un usuario existente, el arranque fallara para obligar a corregir la configuracion.
- Si activas `REQUIRE_EXISTING_DB=1`, el servicio fallara al arrancar cuando no exista `APP_DB_PATH`; esto evita que Railway levante una instalacion nueva en silencio sobre un volumen vacio o incorrecto.
- Si realmente necesitas el bootstrap manual otra vez, debes habilitarlo de forma explicita con `ALLOW_OWNER_BOOTSTRAP_UI=1`. No queda activo por defecto en Railway.
- Despues del primer deploy estable, conviene borrar `OWNER_BOOTSTRAP_PASSWORD` de Railway o rotarla desde el propio panel owner.

Puedes partir de este archivo de ejemplo: `.env.railway.example`.

## Estado funcional actual

- Dashboard financiero con disponible recomendado, gasto mensual y cobertura.
- CRUD de movimientos con edicion y borrado.
- CRUD de ingresos fijos esperados.
- CRUD de obligaciones.
- Sugerencia de distribucion al registrar ingresos.
- Insights y buckets mensuales derivados del dominio original.
- Importacion de un archivo legado `prep_personal.db` desde la propia interfaz web.
