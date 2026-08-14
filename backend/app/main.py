from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Database, UserRecord
from .importer import import_flutter_database
from .schemas import AdminBootstrapRequest, AuthStatus, CategoryConfigInput, CreditCardCreate, CreditCardStatementCreate, FixedIncomeSourceCreate, FlutterImportSummary, InitialSetupPayload, LoginRequest, LoginResponse, ObligationCreate, OwnerPanelResponse, PasswordChangeRequest, TagConfigInput, ThemePreferenceUpdate, TransactionCreate, UserAccessUpdateRequest, UserCreateRequest
from .services import FinancialSnapshot, build_bootstrap, suggest_income_allocation


database = Database()
logger = logging.getLogger(__name__)


def _env_flag(name: str) -> bool:
    return os.getenv(name, '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _is_hosted_environment() -> bool:
    return any(name.startswith('RAILWAY_') for name in os.environ)


def _manual_owner_bootstrap_enabled() -> bool:
    if _env_flag('ALLOW_OWNER_BOOTSTRAP_UI'):
        return True
    return not _is_hosted_environment()


def _owner_bootstrap_env_presence() -> tuple[bool, bool]:
    has_username = bool(os.getenv('OWNER_BOOTSTRAP_USERNAME', '').strip())
    has_password = bool(os.getenv('OWNER_BOOTSTRAP_PASSWORD', '').strip())
    return has_username, has_password


def _require_existing_db(database_path: str) -> None:
    if not _env_flag('REQUIRE_EXISTING_DB'):
        return
    db_file = Path(database_path)
    if db_file.exists():
        return
    raise RuntimeError(
        f'REQUIRE_EXISTING_DB=1 impidio iniciar porque la base esperada no existe: {database_path}. '
        'Esto suele indicar un volumen persistente nuevo, vacio o mal montado en Railway.'
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.startup_warning = None
    db_file = Path(database.db_path)
    existed_before_startup = db_file.exists()
    _require_existing_db(database.db_path)
    database.initialize()
    try:
        database.auto_bootstrap_owner_from_env()
    except RuntimeError as exc:
        database.startup_warning = str(exc)
        logger.exception('Owner bootstrap automatico omitido: %s', exc)

    has_users = database.has_users()
    has_owner = database.has_owner()
    db_exists = db_file.exists()
    db_size = db_file.stat().st_size if db_exists else 0
    logger.warning(
        'Startup DB diagnostics | path=%s | existed_before=%s | exists_now=%s | size=%s | has_users=%s | has_owner=%s',
        database.db_path,
        existed_before_startup,
        db_exists,
        db_size,
        has_users,
        has_owner,
    )

    if not has_owner:
        warning_parts: list[str] = []
        has_owner_bootstrap_username, has_owner_bootstrap_password = _owner_bootstrap_env_presence()
        if database.startup_warning:
            warning_parts.append(database.startup_warning)
        warning_parts.append(f'No existe cuenta owner en la base activa ({database.db_path}).')
        if not existed_before_startup:
            warning_parts.append('Este arranque creo un archivo SQLite nuevo; si esperabas tus usuarios anteriores, revisa el volumen persistente de Railway.')
        if any(name.startswith('RAILWAY_') for name in os.environ) and not database.db_path.startswith('/data/'):
            warning_parts.append('APP_DB_PATH no apunta a /data. Define APP_DB_PATH=/data/gride_ledger.db y monta el volumen en /data.')
        if _is_hosted_environment() and not _manual_owner_bootstrap_enabled():
            warning_parts.append('El bootstrap manual owner esta deshabilitado en Railway. Crea la cuenta owner con OWNER_BOOTSTRAP_USERNAME y OWNER_BOOTSTRAP_PASSWORD, o vuelve a montar la base persistente correcta.')
            warning_parts.append(
                f'Variables detectadas en runtime: OWNER_BOOTSTRAP_USERNAME={"si" if has_owner_bootstrap_username else "no"}, OWNER_BOOTSTRAP_PASSWORD={"si" if has_owner_bootstrap_password else "no"}.'
            )
        database.startup_warning = ' '.join(warning_parts)
    yield


app = FastAPI(title='Gride Ledger API', version='2.0.0', lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])


def current_state(user_id: int):
    fixed_income_sources = database.list_fixed_income_sources(user_id)
    obligations = database.list_obligations(user_id)
    credit_cards = database.list_credit_cards(user_id)
    credit_card_statements = database.list_credit_card_statements(user_id)
    transactions = database.list_transactions(user_id)
    categories = database.list_categories(user_id)
    tags = database.list_tags(user_id)
    return fixed_income_sources, obligations, credit_cards, credit_card_statements, transactions, categories, tags


def require_auth(x_session_token: str | None = Header(default=None)) -> UserRecord:
    user = database.get_session_user(x_session_token)
    if user is None:
        raise HTTPException(status_code=401, detail='Sesion requerida.')
    return user


def require_editor(user: UserRecord = Depends(require_auth)) -> UserRecord:
    if not user.can_edit_data:
        raise HTTPException(status_code=403, detail='Tu cuenta no tiene permisos para editar datos.')
    return user


def require_admin(user: UserRecord = Depends(require_auth)) -> UserRecord:
    if not user.can_manage_users:
        raise HTTPException(status_code=403, detail='Solo la cuenta administradora puede gestionar usuarios.')
    return user


def require_owner(user: UserRecord = Depends(require_auth)) -> UserRecord:
    if not user.is_owner or not user.active:
        raise HTTPException(status_code=403, detail='Solo la cuenta owner puede acceder a este panel.')
    return user


def require_app_user(user: UserRecord = Depends(require_auth)) -> UserRecord:
    if user.is_owner:
        raise HTTPException(status_code=403, detail='La cuenta owner usa el panel /owner.')
    return user


@app.get('/api/health')
def healthcheck() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/auth/status', response_model=AuthStatus)
def auth_status(x_session_token: str | None = Header(default=None)):
    user = database.get_session_user(x_session_token)
    bootstrap_needed = database.admin_bootstrap_required()
    bootstrap_enabled = bootstrap_needed and _manual_owner_bootstrap_enabled()
    return AuthStatus(authenticated=user is not None, has_users=database.has_users(), admin_bootstrap_required=bootstrap_enabled, owner_bootstrap_enabled=bootstrap_enabled, admin_bootstrap_code_path=database.bootstrap_code_path if bootstrap_enabled else None, owner_bootstrap_warning=database.startup_warning, setup_complete=user.setup_complete if user else False, username=user.username if user else None, role=user.role if user else None, can_edit_data=user.can_edit_data if user else False, can_manage_users=user.can_manage_users if user else False)


@app.post('/api/auth/bootstrap-owner', response_model=LoginResponse)
def bootstrap_owner(payload: AdminBootstrapRequest):
    if not _manual_owner_bootstrap_enabled():
        raise HTTPException(status_code=403, detail='El bootstrap manual owner esta deshabilitado en este entorno. Configura OWNER_BOOTSTRAP_USERNAME y OWNER_BOOTSTRAP_PASSWORD para crear la cuenta owner inicial.')
    try:
        user = database.bootstrap_owner(payload.username, payload.password, payload.bootstrap_code)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    session_token = database.create_session(user.id, payload.device_name)
    return LoginResponse(authenticated=True, has_users=True, setup_complete=user.setup_complete, username=user.username, role=user.role, can_edit_data=user.can_edit_data, can_manage_users=user.can_manage_users, session_token=session_token)


@app.post('/api/auth/bootstrap-admin', response_model=LoginResponse)
def bootstrap_admin_compat(payload: AdminBootstrapRequest):
    return bootstrap_owner(payload)


@app.post('/api/auth/login', response_model=LoginResponse)
def login(payload: LoginRequest):
    try:
        user = database.authenticate_app_user(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    session_token = database.create_session(user.id, payload.device_name)
    return LoginResponse(authenticated=True, has_users=True, setup_complete=user.setup_complete, username=user.username, role=user.role, can_edit_data=user.can_edit_data, can_manage_users=user.can_manage_users, session_token=session_token)


@app.post('/api/auth/login-owner', response_model=LoginResponse)
def login_owner(payload: LoginRequest):
    try:
        user = database.authenticate_owner(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    session_token = database.create_session(user.id, payload.device_name)
    return LoginResponse(authenticated=True, has_users=True, setup_complete=user.setup_complete, username=user.username, role=user.role, can_edit_data=user.can_edit_data, can_manage_users=user.can_manage_users, session_token=session_token)


@app.post('/api/auth/logout', status_code=204)
def logout(user: UserRecord = Depends(require_auth), x_session_token: str | None = Header(default=None)):
    del user
    database.revoke_session(x_session_token)


@app.post('/api/auth/change-password', status_code=204)
def change_password(payload: PasswordChangeRequest, user: UserRecord = Depends(require_auth)):
    if not database.verify_password(user.id, payload.current_password):
        raise HTTPException(status_code=401, detail='La contrasena actual no coincide.')
    database.set_password(user.id, payload.new_password)
    database.revoke_all_sessions(user.id)


@app.post('/api/users')
def create_user(payload: UserCreateRequest, user: UserRecord = Depends(require_owner)):
    try:
        return database.create_user(user, payload.username, payload.password, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put('/api/users/{user_id}/access')
def update_user_access(user_id: int, payload: UserAccessUpdateRequest, user: UserRecord = Depends(require_owner)):
    try:
        return database.update_user_access(user, user_id, payload.role, payload.active)
    except ValueError as exc:
        status_code = 404 if 'no encontrado' in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.delete('/api/users/{user_id}', status_code=204)
def delete_user(user_id: int, user: UserRecord = Depends(require_owner)):
    try:
        database.delete_user(user, user_id)
    except ValueError as exc:
        status_code = 404 if 'no encontrado' in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.get('/api/owner/panel', response_model=OwnerPanelResponse)
def owner_panel(user: UserRecord = Depends(require_owner)):
    return OwnerPanelResponse(current_username=user.username, current_user_role=user.role, users=database.list_owner_panel_users(), audit_events=database.list_audit_events(limit=80))


@app.get('/api/bootstrap')
def bootstrap(user: UserRecord = Depends(require_app_user)):
    payload = build_bootstrap(*current_state(user.id))
    payload.setup_complete = database.is_setup_complete(user.id)
    payload.theme_id = database.get_theme_id(user.id)
    payload.current_username = user.username
    payload.current_user_role = user.role
    payload.can_manage_users = user.can_manage_users
    payload.can_edit_data = user.can_edit_data
    payload.users = database.list_users() if user.can_manage_users else []
    payload.audit_events = database.list_audit_events() if user.can_manage_users else []
    return payload


@app.get('/api/suggestions/income')
def income_suggestion(amount: float, user: UserRecord = Depends(require_app_user)):
    fixed_income_sources, obligations, _, _, transactions, _, _ = current_state(user.id)
    snapshot = FinancialSnapshot(fixed_income_expected=sum(item.amount for item in fixed_income_sources if item.active), income_reported=sum(item.amount for item in transactions if item.kind == 'ingreso'), pending_obligations=sum(item.amount for item in obligations if item.status != 'Cubierto'))
    return suggest_income_allocation(amount, snapshot)


@app.post('/api/fixed-income-sources')
def create_fixed_income_source(payload: FixedIncomeSourceCreate, user: UserRecord = Depends(require_editor)):
    return database.create_fixed_income_source(user.id, payload.model_dump())


@app.put('/api/fixed-income-sources/{item_id}')
def update_fixed_income_source(item_id: int, payload: FixedIncomeSourceCreate, user: UserRecord = Depends(require_editor)):
    try:
        return database.update_fixed_income_source(user.id, item_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete('/api/fixed-income-sources/{item_id}', status_code=204)
def delete_fixed_income_source(item_id: int, user: UserRecord = Depends(require_editor)):
    database.delete_fixed_income_source(user.id, item_id)


@app.post('/api/obligations')
def create_obligation(payload: ObligationCreate, user: UserRecord = Depends(require_editor)):
    return database.create_obligation(user.id, payload.model_dump())


@app.put('/api/obligations/{item_id}')
def update_obligation(item_id: int, payload: ObligationCreate, user: UserRecord = Depends(require_editor)):
    try:
        return database.update_obligation(user.id, item_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete('/api/obligations/{item_id}', status_code=204)
def delete_obligation(item_id: int, user: UserRecord = Depends(require_editor)):
    database.delete_obligation(user.id, item_id)


@app.post('/api/credit-cards')
def create_credit_card(payload: CreditCardCreate, user: UserRecord = Depends(require_editor)):
    return database.create_credit_card(user.id, payload.model_dump())


@app.put('/api/credit-cards/{item_id}')
def update_credit_card(item_id: int, payload: CreditCardCreate, user: UserRecord = Depends(require_editor)):
    try:
        return database.update_credit_card(user.id, item_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete('/api/credit-cards/{item_id}', status_code=204)
def delete_credit_card(item_id: int, user: UserRecord = Depends(require_editor)):
    database.delete_credit_card(user.id, item_id)


@app.post('/api/credit-card-statements')
def create_credit_card_statement(payload: CreditCardStatementCreate, user: UserRecord = Depends(require_editor)):
    try:
        return database.create_credit_card_statement(user.id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put('/api/credit-card-statements/{item_id}')
def update_credit_card_statement(item_id: int, payload: CreditCardStatementCreate, user: UserRecord = Depends(require_editor)):
    try:
        return database.update_credit_card_statement(user.id, item_id, payload.model_dump())
    except ValueError as exc:
        status_code = 404 if 'no encontrado' in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.delete('/api/credit-card-statements/{item_id}', status_code=204)
def delete_credit_card_statement(item_id: int, user: UserRecord = Depends(require_editor)):
    database.delete_credit_card_statement(user.id, item_id)


@app.post('/api/transactions')
def create_transaction(payload: TransactionCreate, user: UserRecord = Depends(require_editor)):
    return database.create_transaction(user.id, payload.model_dump())


@app.put('/api/transactions/{item_id}')
def update_transaction(item_id: int, payload: TransactionCreate, user: UserRecord = Depends(require_editor)):
    try:
        return database.update_transaction(user.id, item_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete('/api/transactions/{item_id}', status_code=204)
def delete_transaction(item_id: int, user: UserRecord = Depends(require_editor)):
    database.delete_transaction(user.id, item_id)


@app.post('/api/categories')
def create_or_update_category(payload: CategoryConfigInput, user: UserRecord = Depends(require_editor)):
    return database.upsert_category(user.id, payload.model_dump())


@app.put('/api/categories/{category_id}')
def update_category(category_id: str, payload: CategoryConfigInput, user: UserRecord = Depends(require_editor)):
    if category_id != payload.id:
        raise HTTPException(status_code=400, detail='El id de la categoria no coincide.')
    return database.upsert_category(user.id, payload.model_dump())


@app.post('/api/tags')
def create_or_update_tag(payload: TagConfigInput, user: UserRecord = Depends(require_editor)):
    return database.upsert_tag(user.id, payload.model_dump())


@app.put('/api/tags/{tag_id}')
def update_tag(tag_id: str, payload: TagConfigInput, user: UserRecord = Depends(require_editor)):
    if tag_id != payload.id:
        raise HTTPException(status_code=400, detail='El id del tag no coincide.')
    return database.upsert_tag(user.id, payload.model_dump())


@app.delete('/api/categories/{category_id}', status_code=204)
def delete_category(category_id: str, user: UserRecord = Depends(require_editor)):
    database.delete_category(user.id, category_id)


@app.delete('/api/tags/{tag_id}', status_code=204)
def delete_tag(tag_id: str, user: UserRecord = Depends(require_editor)):
    database.delete_tag(user.id, tag_id)


@app.put('/api/preferences/theme', status_code=204)
def update_theme_preference(payload: ThemePreferenceUpdate, user: UserRecord = Depends(require_app_user)):
    database.set_theme_id(user.id, payload.theme_id)
    database.record_audit(user, 'update_theme', 'preference', payload.theme_id, 'Tema actualizado en esta cuenta.')


@app.post('/api/import/flutter-db', response_model=FlutterImportSummary)
async def import_flutter_db(file: UploadFile = File(...), replace_existing: bool = Form(True), user: UserRecord = Depends(require_editor)):
    suffix = Path(file.filename or 'prep_personal.db').suffix or '.db'
    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        temporary_file.write(await file.read())
        temp_path = temporary_file.name

    try:
        result = import_flutter_database(temp_path, database, user.id, replace_existing=replace_existing)
        database.set_setup_complete(user.id, True)
        database.record_audit(user, 'import_flutter_db', 'import', file.filename or 'flutter.db', f'Reemplazar existentes: {replace_existing}.')
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail='No se encontro el archivo temporal para importar.') from exc
    except (json.JSONDecodeError, OSError, ValueError, sqlite3.DatabaseError) as exc:
        raise HTTPException(status_code=400, detail=f'No se pudo importar la base Flutter: {exc}') from exc
    finally:
        Path(temp_path).unlink(missing_ok=True)


@app.post('/api/setup/complete')
def complete_initial_setup(payload: InitialSetupPayload, user: UserRecord = Depends(require_editor)):
    database.complete_initial_setup(
        user.id,
        [item.model_dump() for item in payload.fixed_income_sources],
        [item.model_dump() for item in payload.obligations],
    )
    response = build_bootstrap(*current_state(user.id))
    response.setup_complete = True
    response.theme_id = database.get_theme_id(user.id)
    response.current_username = user.username
    response.current_user_role = user.role
    response.can_manage_users = user.can_manage_users
    response.can_edit_data = user.can_edit_data
    response.users = database.list_users() if user.can_manage_users else []
    response.audit_events = database.list_audit_events() if user.can_manage_users else []
    database.record_audit(user, 'complete_setup', 'setup', user.username, 'Wizard inicial completado.')
    return response


@app.post('/api/setup/reset', status_code=204)
def reset_initial_setup(user: UserRecord = Depends(require_editor)):
    database.reset_financial_setup(user.id)
    database.record_audit(user, 'reset_setup', 'setup', user.username, 'Configuracion inicial reiniciada.')


frontend_dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if frontend_dist.exists():
    app.mount('/assets', StaticFiles(directory=frontend_dist / 'assets'), name='assets')

    @app.get('/')
    def serve_index():
        return FileResponse(frontend_dist / 'index.html')

    @app.get('/{full_path:path}')
    def serve_spa(full_path: str):
        candidate = frontend_dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / 'index.html')