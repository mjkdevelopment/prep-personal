import os
import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app, database
from backend.app.main import _require_existing_db
from backend.app.main import _manual_owner_bootstrap_enabled
from backend.app.schemas import UserRole


client = TestClient(app)
_temp_directory: TemporaryDirectory[str] | None = None


def bootstrap_owner(username: str = 'owner', password: str = '1234') -> dict[str, str]:
    bootstrap_code = Path(database.bootstrap_code_path).read_text(encoding='utf-8').strip()
    response = client.post('/api/auth/bootstrap-owner', json={'username': username, 'password': password, 'bootstrap_code': bootstrap_code, 'device_name': 'pytest'})
    assert response.status_code == 200
    token = response.json()['session_token']
    return {'x-session-token': token}


def owner_headers(username: str = 'owner', password: str = '1234') -> dict[str, str]:
    response = client.post('/api/auth/login-owner', json={'username': username, 'password': password, 'device_name': 'pytest'})
    assert response.status_code == 200
    token = response.json()['session_token']
    return {'x-session-token': token}


def ensure_owner_headers(username: str = 'owner', password: str = '1234') -> dict[str, str]:
    status = client.get('/api/auth/status')
    if status.status_code == 200 and status.json()['admin_bootstrap_required'] is True:
        return bootstrap_owner(username, password)
    return owner_headers(username, password)


def app_headers(username: str = 'demo', password: str = '1234') -> dict[str, str]:
    response = client.post('/api/auth/login', json={'username': username, 'password': password, 'device_name': 'pytest'})
    assert response.status_code == 200
    token = response.json()['session_token']
    return {'x-session-token': token}


def ensure_app_headers(username: str = 'demo', password: str = '1234', role: str = 'operator') -> dict[str, str]:
    login_response = client.post('/api/auth/login', json={'username': username, 'password': password, 'device_name': 'pytest'})
    if login_response.status_code == 200:
        token = login_response.json()['session_token']
        return {'x-session-token': token}

    headers = ensure_owner_headers()
    create_response = client.post('/api/users', json={'username': username, 'password': password, 'role': role}, headers=headers)
    assert create_response.status_code in {200, 400}
    response = client.post('/api/auth/login', json={'username': username, 'password': password, 'device_name': 'pytest'})
    assert response.status_code == 200
    token = response.json()['session_token']
    return {'x-session-token': token}


def setup_module() -> None:
    global _temp_directory
    _temp_directory = TemporaryDirectory()
    database.db_path = str(Path(_temp_directory.name) / 'test_app.db')
    database.initialize()


def teardown_module() -> None:
    if _temp_directory is not None:
        _temp_directory.cleanup()


def test_healthcheck() -> None:
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_bootstrap_contains_dashboard() -> None:
    response = client.get('/api/bootstrap', headers=ensure_app_headers())
    assert response.status_code == 200
    payload = response.json()
    assert 'dashboard' in payload
    assert 'theme_id' in payload
    assert 'setup_complete' in payload
    assert 'transactions' in payload
    assert 'categories' in payload
    assert payload['current_user_role'] == 'operator'
    assert payload['can_edit_data'] is True
    assert payload['can_manage_users'] is False
    assert payload['audit_events'] == []
    assert payload['users'] == []


def test_auth_status_requires_login_for_authenticated_state() -> None:
    response = client.get('/api/auth/status')
    assert response.status_code == 200
    assert response.json()['authenticated'] is False
    assert response.json()['has_users'] in {False, True}

    authenticated = client.get('/api/auth/status', headers=ensure_owner_headers())
    assert authenticated.status_code == 200
    assert authenticated.json()['authenticated'] is True
    assert authenticated.json()['username'] == 'owner'
    assert authenticated.json()['admin_bootstrap_required'] is False
    assert authenticated.json()['role'] == 'owner'
    assert authenticated.json()['can_manage_users'] is True


def test_imports_flutter_database_file() -> None:
    assert _temp_directory is not None
    legacy_db_path = Path(_temp_directory.name) / 'prep_personal_legacy.db'
    legacy_connection = sqlite3.connect(legacy_db_path)
    try:
        legacy_connection.execute('CREATE TABLE fixed_income_sources(id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, amount REAL NOT NULL, cadence TEXT NOT NULL, expected_day INTEGER NOT NULL, expected_weekday INTEGER, wallet TEXT NOT NULL, active INTEGER NOT NULL)')
        legacy_connection.execute('CREATE TABLE obligations(id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, amount REAL NOT NULL, category_id TEXT, cadence TEXT NOT NULL, due_day INTEGER NOT NULL, due_weekday INTEGER, kind TEXT NOT NULL, status TEXT NOT NULL)')
        legacy_connection.execute('CREATE TABLE transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, amount REAL NOT NULL, wallet TEXT NOT NULL, category TEXT NOT NULL, tags TEXT NOT NULL, notes TEXT NOT NULL, date_iso TEXT NOT NULL, recurring INTEGER NOT NULL)')
        legacy_connection.execute('CREATE TABLE app_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at_iso TEXT NOT NULL)')
        legacy_connection.execute("INSERT INTO fixed_income_sources(label, amount, cadence, expected_day, expected_weekday, wallet, active) VALUES('Nomina principal', 5000, 'monthly', 30, NULL, 'Banco', 1)")
        legacy_connection.execute("INSERT INTO obligations(label, amount, category_id, cadence, due_day, due_weekday, kind, status) VALUES('Casa', 1500, 'casa', 'monthly', 15, NULL, 'Fija', 'Pendiente')")
        legacy_connection.execute("INSERT INTO transactions(kind, amount, wallet, category, tags, notes, date_iso, recurring) VALUES('ingreso', 5000, 'Banco', 'Nomina', 'Migrado|Test', 'Ingreso inicial', '2026-08-01T08:00:00', 0)")
        legacy_connection.execute('INSERT INTO app_meta(key, value, updated_at_iso) VALUES(?, ?, ?)', ('category_configs', json.dumps([{'id': 'viajes', 'label': 'Viajes', 'scope': 'expense', 'type': 'Variable', 'colorToken': 'plum', 'iconToken': 'flight', 'active': True}]), '2026-08-01T00:00:00'))
        legacy_connection.execute('INSERT INTO app_meta(key, value, updated_at_iso) VALUES(?, ?, ?)', ('tag_configs', json.dumps([{'id': 'migrado', 'label': 'Migrado', 'colorToken': 'sage', 'active': True}]), '2026-08-01T00:00:00'))
        legacy_connection.commit()
    finally:
        legacy_connection.close()

    headers = ensure_app_headers('importer', '1234')
    with legacy_db_path.open('rb') as database_file:
        response = client.post('/api/import/flutter-db', files={'file': ('prep_personal.db', database_file, 'application/octet-stream')}, data={'replace_existing': 'true'}, headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload['fixed_income_sources'] == 1
    assert payload['obligations'] == 1
    assert payload['transactions'] == 1

    bootstrap = client.get('/api/bootstrap', headers=headers)
    assert bootstrap.status_code == 200
    bootstrap_payload = bootstrap.json()
    assert any(item['label'] == 'Nomina principal' for item in bootstrap_payload['fixed_income_sources'])
    assert any(item['label'] == 'Casa' for item in bootstrap_payload['obligations'])
    assert bootstrap_payload['transactions'][0]['tags'] == ['Migrado', 'Test']
    assert any(item['label'] == 'Viajes' for item in bootstrap_payload['categories'])
    assert any(item['label'] == 'Migrado' for item in bootstrap_payload['tags'])
    assert bootstrap_payload['setup_complete'] is True


def test_complete_and_reset_setup_flow() -> None:
    headers = ensure_app_headers('setupuser', '1234')
    response = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Salario base',
                    'amount': 4200,
                    'cadence': 'monthly',
                    'expected_day': 30,
                    'expected_weekday': None,
                    'wallet': 'Banco',
                    'active': True,
                }
            ],
            'obligations': [
                {
                    'label': 'Casa',
                    'amount': 1400,
                    'category_id': 'casa',
                    'cadence': 'monthly',
                    'due_day': 15,
                    'due_weekday': None,
                    'kind': 'Fija',
                    'status': 'Pendiente',
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['setup_complete'] is True
    assert len(payload['fixed_income_sources']) == 1
    assert len(payload['obligations']) == 1
    assert payload['transactions'] == []

    reset_response = client.post('/api/setup/reset', headers=headers)
    assert reset_response.status_code == 204

    bootstrap = client.get('/api/bootstrap', headers=headers)
    bootstrap_payload = bootstrap.json()
    assert bootstrap_payload['setup_complete'] is False
    assert bootstrap_payload['fixed_income_sources'] == []
    assert bootstrap_payload['obligations'] == []
    assert bootstrap_payload['transactions'] == []


def test_dashboard_monthly_expected_converts_weekly_and_biweekly_amounts() -> None:
    headers = ensure_app_headers('cadenceuser', '1234')
    response = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Semanal base',
                    'amount': 7500,
                    'cadence': 'weekly',
                    'expected_day': 30,
                    'expected_weekday': 1,
                    'wallet': 'Banco',
                    'active': True,
                },
                {
                    'label': 'Quincenal base',
                    'amount': 12000,
                    'cadence': 'biweekly',
                    'expected_day': 15,
                    'expected_weekday': None,
                    'wallet': 'Banco',
                    'active': True,
                },
            ],
            'obligations': [
                {
                    'label': 'Servicio semanal',
                    'amount': 5000,
                    'category_id': 'casa',
                    'cadence': 'weekly',
                    'due_day': 15,
                    'due_weekday': 1,
                    'kind': 'Fija',
                    'status': 'Pendiente',
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['dashboard']['fixed_income_expected'] == 54000
    assert payload['dashboard']['monthly_fixed_outflow_total'] == 20000
    assert payload['dashboard']['reserve_per_quincena'] == 10000
    assert payload['dashboard']['quincena_reserve_views'][1]['amount'] == 10000
    assert payload['dashboard']['quincena_reserve_views'][2]['amount'] == 10000


def test_category_and_tag_upsert_require_auth() -> None:
    headers = ensure_app_headers('cataloguser', '1234')
    category_response = client.post('/api/categories', json={'id': 'mascotas', 'label': 'Mascotas', 'scope': 'expense', 'type': 'Variable', 'color_token': 'plum', 'icon_token': 'favorite', 'active': True}, headers=headers)
    tag_response = client.post('/api/tags', json={'id': 'veterinaria', 'label': 'Veterinaria', 'color_token': 'sage', 'active': True}, headers=headers)

    assert category_response.status_code == 200
    assert category_response.json()['icon_token'] == 'favorite'
    assert tag_response.status_code == 200
    assert tag_response.json()['label'] == 'Veterinaria'


def test_theme_preference_and_hard_deletes() -> None:
    headers = ensure_app_headers('themeuser', '1234')
    client.post('/api/categories', json={'id': 'ocio', 'label': 'Ocio', 'scope': 'expense', 'type': 'Variable', 'color_token': 'coral', 'icon_token': 'tv', 'active': True}, headers=headers)
    client.post('/api/tags', json={'id': 'cine', 'label': 'Cine', 'color_token': 'plum', 'active': True}, headers=headers)

    theme_response = client.put('/api/preferences/theme', json={'theme_id': 'ocean_ledger'}, headers=headers)
    assert theme_response.status_code == 204

    delete_category_response = client.delete('/api/categories/ocio', headers=headers)
    delete_tag_response = client.delete('/api/tags/cine', headers=headers)
    assert delete_category_response.status_code == 204
    assert delete_tag_response.status_code == 204

    bootstrap = client.get('/api/bootstrap', headers=headers)
    payload = bootstrap.json()
    assert payload['theme_id'] == 'ocean_ledger'
    assert all(item['id'] != 'ocio' for item in payload['categories'])
    assert all(item['id'] != 'cine' for item in payload['tags'])


def test_admin_can_create_user_and_data_is_isolated() -> None:
    owner_headers = ensure_owner_headers()
    create_response = client.post('/api/users', json={'username': 'carlos', 'password': 'abcd', 'role': 'viewer'}, headers=owner_headers)
    assert create_response.status_code == 200
    assert create_response.json()['username'] == 'carlos'
    assert create_response.json()['role'] == 'viewer'

    operator_headers = ensure_app_headers('operador1', 'abcd')
    operator_create = client.post('/api/fixed-income-sources', json={'label': 'Owner', 'amount': 1000, 'cadence': 'monthly', 'expected_day': 30, 'expected_weekday': None, 'wallet': 'Banco', 'active': True}, headers=operator_headers)
    assert operator_create.status_code == 200

    carlos_headers = app_headers('carlos', 'abcd')
    carlos_bootstrap = client.get('/api/bootstrap', headers=carlos_headers)
    assert carlos_bootstrap.status_code == 200
    carlos_payload = carlos_bootstrap.json()
    assert carlos_payload['current_username'] == 'carlos'
    assert carlos_payload['current_user_role'] == 'viewer'
    assert carlos_payload['fixed_income_sources'] == []
    assert carlos_payload['can_manage_users'] is False
    assert carlos_payload['can_edit_data'] is False

    owner_panel = client.get('/api/owner/panel', headers=owner_headers)
    assert owner_panel.status_code == 200
    assert any(event['action'] == 'create_user' and event['target_value'] == 'carlos' for event in owner_panel.json()['audit_events'])


def test_viewer_cannot_write_and_admin_can_update_access() -> None:
    owner_headers = ensure_owner_headers()
    create_response = client.post('/api/users', json={'username': 'maria', 'password': 'abcd', 'role': 'viewer'}, headers=owner_headers)
    assert create_response.status_code == 200
    maria_id = create_response.json()['id']

    maria_headers = app_headers('maria', 'abcd')
    viewer_create = client.post('/api/transactions', json={'kind': 'gasto', 'amount': 10, 'wallet': 'Banco', 'category': 'Casa', 'tags': [], 'notes': '', 'date': '2026-08-01T08:00:00', 'recurring': False}, headers=maria_headers)
    assert viewer_create.status_code == 403

    elevate = client.put(f'/api/users/{maria_id}/access', json={'role': 'operator', 'active': True}, headers=owner_headers)
    assert elevate.status_code == 200
    assert elevate.json()['role'] == 'operator'

    updated_login = app_headers('maria', 'abcd')
    operator_create = client.post('/api/transactions', json={'kind': 'gasto', 'amount': 10, 'wallet': 'Banco', 'category': 'Casa', 'tags': [], 'notes': '', 'date': '2026-08-01T08:00:00', 'recurring': False}, headers=updated_login)
    assert operator_create.status_code == 200


def test_first_run_requires_bootstrap_code() -> None:
    assert _temp_directory is not None
    first_run_db = str(Path(_temp_directory.name) / 'first_run_only.db')
    database.db_path = first_run_db
    database.initialize()

    response = client.get('/api/auth/status')
    assert response.status_code == 200
    assert response.json()['admin_bootstrap_required'] is True
    assert response.json()['has_users'] is False

    database.db_path = str(Path(_temp_directory.name) / 'test_app.db')


def test_manual_owner_bootstrap_disabled_in_hosted_environment_by_default() -> None:
    with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production'}, clear=False):
        assert _manual_owner_bootstrap_enabled() is False


def test_bootstrap_owner_rejected_when_manual_bootstrap_disabled() -> None:
    with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production'}, clear=False):
        response = client.post('/api/auth/bootstrap-owner', json={'username': 'owner', 'password': '1234', 'bootstrap_code': 'ignored-code', 'device_name': 'pytest'})
    assert response.status_code == 403


def test_hosted_warning_reports_owner_bootstrap_env_presence() -> None:
    assert _temp_directory is not None
    hosted_db = str(Path(_temp_directory.name) / 'hosted_env_presence.db')
    database.db_path = hosted_db
    previous_warning = database.startup_warning
    try:
        with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production'}, clear=False):
            os.environ.pop('OWNER_BOOTSTRAP_USERNAME', None)
            os.environ.pop('OWNER_BOOTSTRAP_PASSWORD', None)
            database.startup_warning = None
            database.initialize()
            if not database.has_owner():
                has_username = bool(os.getenv('OWNER_BOOTSTRAP_USERNAME', '').strip())
                has_password = bool(os.getenv('OWNER_BOOTSTRAP_PASSWORD', '').strip())
                warning_parts = [
                    f'No existe cuenta owner en la base activa ({database.db_path}).',
                    'El bootstrap manual owner esta deshabilitado en Railway. Crea la cuenta owner con OWNER_BOOTSTRAP_USERNAME y OWNER_BOOTSTRAP_PASSWORD, o vuelve a montar la base persistente correcta.',
                    f'Variables detectadas en runtime: OWNER_BOOTSTRAP_USERNAME={"si" if has_username else "no"}, OWNER_BOOTSTRAP_PASSWORD={"si" if has_password else "no"}.',
                ]
                database.startup_warning = ' '.join(warning_parts)

            status = client.get('/api/auth/status')
            assert status.status_code == 200
            assert 'OWNER_BOOTSTRAP_USERNAME=no, OWNER_BOOTSTRAP_PASSWORD=no.' in status.json()['owner_bootstrap_warning']
    finally:
        database.startup_warning = previous_warning
        database.db_path = str(Path(_temp_directory.name) / 'test_app.db')


def test_owner_bootstrap_env_pair_not_required_when_owner_already_exists() -> None:
    assert _temp_directory is not None
    existing_owner_db = str(Path(_temp_directory.name) / 'existing_owner_env_pair.db')
    previous_db_path = database.db_path
    database.db_path = existing_owner_db
    try:
        database.initialize()
        with database.connect() as connection:
            theme_id = database._get_meta_value(connection, 'theme_id') or 'emerald_editorial'
            database._insert_user(connection, 'owner-env', '1234', UserRole.owner, theme_id, False, None)

        with patch.dict(os.environ, {'OWNER_BOOTSTRAP_USERNAME': 'owner-env-only'}, clear=False):
            os.environ.pop('OWNER_BOOTSTRAP_PASSWORD', None)
            assert database.auto_bootstrap_owner_from_env() is False
    finally:
        database.db_path = previous_db_path


def test_bootstrap_admin_rejects_bad_code_on_clean_db() -> None:
    assert _temp_directory is not None
    second_db = str(Path(_temp_directory.name) / 'clean_second.db')
    database.db_path = second_db
    database.initialize()

    status = client.get('/api/auth/status')
    assert status.status_code == 200
    assert status.json()['has_users'] is False
    assert status.json()['admin_bootstrap_required'] is True

    bad = client.post('/api/auth/bootstrap-owner', json={'username': 'root2', 'password': '1234', 'bootstrap_code': 'incorrecto', 'device_name': 'pytest'})
    assert bad.status_code == 401

    ok_headers = bootstrap_owner('root2', '1234')
    ok_status = client.get('/api/auth/status', headers=ok_headers)
    assert ok_status.status_code == 200
    assert ok_status.json()['username'] == 'root2'
    assert ok_status.json()['role'] == 'owner'

    database.db_path = str(Path(_temp_directory.name) / 'test_app.db')


def test_owner_bootstrap_recovers_database_with_users_but_no_owner() -> None:
    assert _temp_directory is not None
    repaired_db = str(Path(_temp_directory.name) / 'repair_owner.db')
    database.db_path = repaired_db
    database.initialize()

    with database.connect() as connection:
        theme_id = database._get_meta_value(connection, 'theme_id') or 'emerald_editorial'
        database._insert_user(connection, 'mjk', 'abcd', UserRole.operator, theme_id, False, None)

    database.initialize()

    status = client.get('/api/auth/status')
    assert status.status_code == 200
    assert status.json()['has_users'] is True
    assert status.json()['admin_bootstrap_required'] is True

    headers = bootstrap_owner('ownerfix', '1234')
    owner_status = client.get('/api/auth/status', headers=headers)
    assert owner_status.status_code == 200
    assert owner_status.json()['username'] == 'ownerfix'
    assert owner_status.json()['role'] == 'owner'
    assert owner_status.json()['admin_bootstrap_required'] is False

    database.db_path = str(Path(_temp_directory.name) / 'test_app.db')


def test_owner_bootstrap_rejects_existing_username_gracefully() -> None:
    assert _temp_directory is not None
    duplicate_db = str(Path(_temp_directory.name) / 'duplicate_owner.db')
    database.db_path = duplicate_db
    database.initialize()

    with database.connect() as connection:
        theme_id = database._get_meta_value(connection, 'theme_id') or 'emerald_editorial'
        database._insert_user(connection, 'mjk', 'abcd', UserRole.operator, theme_id, False, None)

    database.initialize()
    bootstrap_code = Path(database.bootstrap_code_path).read_text(encoding='utf-8').strip()
    response = client.post('/api/auth/bootstrap-owner', json={'username': 'mjk', 'password': 'abcd', 'bootstrap_code': bootstrap_code, 'device_name': 'pytest'})
    assert response.status_code == 401
    assert response.json()['detail'] == 'Ese usuario ya existe. Usa otro nombre para la cuenta owner.'

    database.db_path = str(Path(_temp_directory.name) / 'test_app.db')


def test_auto_bootstrap_owner_from_env_only_runs_once() -> None:
    assert _temp_directory is not None
    env_db = str(Path(_temp_directory.name) / 'env_owner.db')
    database.db_path = env_db
    database.initialize()

    original_username = os.environ.get('OWNER_BOOTSTRAP_USERNAME')
    original_password = os.environ.get('OWNER_BOOTSTRAP_PASSWORD')
    original_theme = os.environ.get('OWNER_BOOTSTRAP_THEME_ID')
    try:
        os.environ['OWNER_BOOTSTRAP_USERNAME'] = 'railowner'
        os.environ['OWNER_BOOTSTRAP_PASSWORD'] = 'railpass'
        os.environ['OWNER_BOOTSTRAP_THEME_ID'] = 'ocean_ledger'

        created = database.auto_bootstrap_owner_from_env()
        assert created is True
        assert database.has_owner() is True

        with database.connect() as connection:
            row = connection.execute("SELECT username, role, theme_id FROM users WHERE role = 'owner' LIMIT 1").fetchone()
            assert row is not None
            assert row['username'] == 'railowner'
            assert row['role'] == 'owner'
            assert row['theme_id'] == 'ocean_ledger'

        created_again = database.auto_bootstrap_owner_from_env()
        assert created_again is False
    finally:
        if original_username is None:
            os.environ.pop('OWNER_BOOTSTRAP_USERNAME', None)
        else:
            os.environ['OWNER_BOOTSTRAP_USERNAME'] = original_username
        if original_password is None:
            os.environ.pop('OWNER_BOOTSTRAP_PASSWORD', None)
        else:
            os.environ['OWNER_BOOTSTRAP_PASSWORD'] = original_password
        if original_theme is None:
            os.environ.pop('OWNER_BOOTSTRAP_THEME_ID', None)
        else:
            os.environ['OWNER_BOOTSTRAP_THEME_ID'] = original_theme
        database.db_path = str(Path(_temp_directory.name) / 'test_app.db')


def test_default_db_path_prefers_data_mount_when_present() -> None:
    railway_env = {key: value for key, value in os.environ.items() if key.startswith('RAILWAY_')}
    try:
        for key in railway_env:
            os.environ.pop(key, None)

        with patch('backend.app.database.Path.is_dir', return_value=True):
            assert database._default_db_path() == '/data/gride_ledger.db'
    finally:
        os.environ.update(railway_env)


def test_require_existing_db_raises_for_missing_file_when_enabled() -> None:
    original = os.environ.get('REQUIRE_EXISTING_DB')
    try:
        os.environ['REQUIRE_EXISTING_DB'] = '1'
        missing_path = str(Path(_temp_directory.name if _temp_directory is not None else '.') / 'missing-production.db')
        try:
            _require_existing_db(missing_path)
            assert False, 'Expected runtime error for missing required database file.'
        except RuntimeError as exc:
            assert 'missing-production.db' in str(exc)
    finally:
        if original is None:
            os.environ.pop('REQUIRE_EXISTING_DB', None)
        else:
            os.environ['REQUIRE_EXISTING_DB'] = original