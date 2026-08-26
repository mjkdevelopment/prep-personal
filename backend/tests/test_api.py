import os
import json
import sqlite3
from datetime import datetime, timedelta
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


def test_emergency_fund_preference_updates_dynamic_target() -> None:
    headers = ensure_app_headers('reserveuser', '1234')
    setup = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Nomina base',
                    'amount': 10000,
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
                    'amount': 4000,
                    'category_id': 'casa',
                    'credit_card_id': None,
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
    assert setup.status_code == 200

    initial = client.get('/api/bootstrap', headers=headers)
    assert initial.status_code == 200
    initial_payload = initial.json()
    assert initial_payload['emergency_fund_months'] == 3
    assert initial_payload['dashboard']['monthly_fixed_outflow_total'] == 4000
    assert initial_payload['dashboard']['emergency_fund_target'] == 12000

    update = client.put('/api/preferences/emergency-fund', json={'emergency_fund_months': 6}, headers=headers)
    assert update.status_code == 204

    refreshed = client.get('/api/bootstrap', headers=headers)
    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()
    assert refreshed_payload['emergency_fund_months'] == 6
    assert refreshed_payload['dashboard']['monthly_fixed_outflow_total'] == 4000
    assert refreshed_payload['dashboard']['emergency_fund_target'] == 24000


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


def test_exports_current_user_backup_as_sqlite() -> None:
    headers = ensure_app_headers('mjk', '1234')
    setup = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Nomina base',
                    'amount': 10000,
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
                    'amount': 4000,
                    'category_id': 'casa',
                    'credit_card_id': None,
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
    assert setup.status_code == 200

    bootstrap = client.get('/api/bootstrap', headers=headers).json()
    obligation_id = bootstrap['obligations'][0]['id']

    transaction = client.post(
        '/api/transactions',
        json={
            'kind': 'gasto',
            'amount': 1500,
            'wallet': 'Banco',
            'category': 'Casa',
            'fixed_income_source_id': None,
            'obligation_id': obligation_id,
            'credit_card_statement_id': None,
            'tags': ['Exportado'],
            'notes': 'Abono de prueba',
            'date': '2026-08-02T10:00:00',
            'recurring': False,
        },
        headers=headers,
    )
    assert transaction.status_code == 200

    export_response = client.get('/api/export/current-db', headers=headers)
    assert export_response.status_code == 200
    assert export_response.headers['content-type'].startswith('application/vnd.sqlite3')

    assert _temp_directory is not None
    export_path = Path(_temp_directory.name) / 'exported_user.sqlite3'
    export_path.write_bytes(export_response.content)

    backup_connection = sqlite3.connect(export_path)
    try:
        fixed_income_count = backup_connection.execute('SELECT COUNT(*) FROM fixed_income_sources').fetchone()[0]
        obligation_count = backup_connection.execute('SELECT COUNT(*) FROM obligations').fetchone()[0]
        transaction_row = backup_connection.execute('SELECT category, tags_json, notes FROM transactions LIMIT 1').fetchone()
        meta_source = backup_connection.execute("SELECT value FROM export_meta WHERE key = 'source'").fetchone()[0]
        table_names = {row[0] for row in backup_connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        backup_connection.close()

    assert fixed_income_count == 1
    assert obligation_count == 1
    assert transaction_row[0] == 'Casa'
    assert 'Exportado' in json.loads(transaction_row[1])
    assert transaction_row[2] == 'Abono de prueba'
    assert meta_source == 'gride_ledger_user_backup_v1'
    assert 'users' not in table_names


def test_export_current_user_backup_is_forbidden_for_other_users() -> None:
    headers = ensure_app_headers('otrodev', '1234')

    response = client.get('/api/export/current-db', headers=headers)

    assert response.status_code == 403
    assert 'solo esta habilitado para la cuenta mjk' in response.json()['detail']


def test_create_debt_and_generate_month_close() -> None:
    headers = ensure_app_headers('debtclose', '1234')
    setup = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Nomina base',
                    'amount': 12000,
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
                    'amount': 3000,
                    'category_id': 'casa',
                    'credit_card_id': None,
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
    assert setup.status_code == 200

    debt_response = client.post(
        '/api/debts',
        json={
            'label': 'Prestamo vehiculo',
            'lender': 'Banco prueba',
            'balance_amount': 250000,
            'monthly_payment_amount': 21000,
            'currency': 'DOP',
            'payment_day': 18,
            'allow_extra_payment': True,
            'active': True,
            'notes': 'Sin penalidad',
        },
        headers=headers,
    )
    assert debt_response.status_code == 200
    assert debt_response.json()['label'] == 'Prestamo vehiculo'

    income_response = client.post(
        '/api/transactions',
        json={
            'kind': 'ingreso',
            'amount': 12000,
            'wallet': 'Banco',
            'category': 'Nomina',
            'fixed_income_source_id': None,
            'obligation_id': None,
            'credit_card_statement_id': None,
            'tags': [],
            'notes': '',
            'date': '2026-08-01T08:00:00',
            'recurring': False,
        },
        headers=headers,
    )
    assert income_response.status_code == 200

    preview_response = client.post('/api/month-close/current/preview', headers=headers)
    assert preview_response.status_code == 200
    preview_snapshot = preview_response.json()
    assert preview_snapshot['is_preview'] is True

    before_official = client.get('/api/bootstrap', headers=headers).json()
    assert before_official['month_close_snapshots'] == []

    close_response = client.post('/api/month-close/current', headers=headers)
    assert close_response.status_code == 200
    snapshot = close_response.json()
    assert snapshot['is_preview'] is False
    assert snapshot['period_month'] >= 1
    assert snapshot['debt_payment_target'] == 21000
    assert snapshot['debt_total_balance'] == 250000
    assert snapshot['overdue_obligations_amount'] >= 0
    assert snapshot['next_cycle_start_buffer'] >= 0
    assert snapshot['goals_shortfall_amount'] >= 0
    assert isinstance(snapshot['highlights'], list)
    assert isinstance(snapshot['next_actions'], list)

    bootstrap = client.get('/api/bootstrap', headers=headers)
    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert len(payload['debts']) == 1
    assert len(payload['month_close_snapshots']) >= 1
    assert payload['dashboard']['debt_total_balance'] == 250000
    assert payload['dashboard']['debt_payment_target'] == 21000
    assert payload['dashboard']['capitalization_target'] == 5400
    assert payload['dashboard']['fixed_cost_ceiling'] == 6000
    assert payload['dashboard']['recommended_free_margin_destination'] in {'Abonar deuda prioritaria', 'Cubrir arrastre vencido'}
    assert isinstance(payload['dashboard']['recommended_free_margin_destination'], str)

    duplicate_close = client.post('/api/month-close/current', headers=headers)
    assert duplicate_close.status_code == 409
    assert 'Ya existe un cierre oficial para este mes' in duplicate_close.json()['detail']


def test_debt_balance_updates_override_manual_amortization_guess() -> None:
    headers = ensure_app_headers('debtupdates', '1234')

    debt_response = client.post(
        '/api/debts',
        json={
            'label': 'Prestamo cooperativa',
            'lender': 'Cooperativa',
            'balance_amount': 830000,
            'monthly_payment_amount': 20000,
            'currency': 'DOP',
            'payment_day': 10,
            'interest_rate_percent': None,
            'interest_rate_period': None,
            'allow_extra_payment': True,
            'active': True,
            'notes': 'Deuda ya en curso',
        },
        headers=headers,
    )
    assert debt_response.status_code == 200
    debt = debt_response.json()
    assert debt['balance_amount'] == 830000
    assert debt['balance_update_count'] >= 1
    assert debt['balance_source'] == 'reported'

    update_response = client.post(
        f"/api/debts/{debt['id']}/balance-updates",
        json={
            'balance_amount': 815000,
            'reported_at_iso': '2026-08-25T12:00:00',
            'notes': 'Saldo confirmado por la app del banco',
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated['balance_amount'] == 815000
    assert updated['last_balance_reported_at_iso'] == '2026-08-25T12:00:00'
    assert updated['balance_update_count'] >= 2
    assert updated['balance_updates'][0]['balance_amount'] == 815000
    assert updated['latest_balance_note'] == 'Saldo confirmado por la app del banco'


def test_debt_transactions_require_linked_debt_and_adjust_balance() -> None:
    headers = ensure_app_headers('debtmovement', '1234')

    debt_a = client.post(
        '/api/debts',
        json={
            'label': 'Vehiculo',
            'lender': 'Dealer',
            'balance_amount': 200000,
            'monthly_payment_amount': 15000,
            'currency': 'DOP',
            'payment_day': 29,
            'interest_rate_percent': None,
            'interest_rate_period': None,
            'allow_extra_payment': True,
            'active': True,
            'notes': '',
        },
        headers=headers,
    )
    assert debt_a.status_code == 200
    debt_b = client.post(
        '/api/debts',
        json={
            'label': 'Cooperativa',
            'lender': 'Coop',
            'balance_amount': 500000,
            'monthly_payment_amount': 22000,
            'currency': 'DOP',
            'payment_day': 15,
            'interest_rate_percent': None,
            'interest_rate_period': None,
            'allow_extra_payment': True,
            'active': True,
            'notes': '',
        },
        headers=headers,
    )
    assert debt_b.status_code == 200

    invalid = client.post(
        '/api/transactions',
        json={
            'kind': 'deuda',
            'amount': 10000,
            'wallet': 'Banco',
            'category': 'Pago deuda',
            'fixed_income_source_id': None,
            'obligation_id': None,
            'credit_card_statement_id': None,
            'debt_id': None,
            'tags': [],
            'notes': 'Sin deuda ligada',
            'date': '2026-08-25T10:00:00',
            'recurring': False,
        },
        headers=headers,
    )
    assert invalid.status_code == 400
    assert 'Selecciona la deuda' in invalid.json()['detail']

    create_payment = client.post(
        '/api/transactions',
        json={
            'kind': 'deuda',
            'amount': 10000,
            'wallet': 'Banco',
            'category': 'Vehiculo',
            'fixed_income_source_id': None,
            'obligation_id': None,
            'credit_card_statement_id': None,
            'debt_id': debt_a.json()['id'],
            'tags': [],
            'notes': 'Abono inicial',
            'date': '2026-08-25T10:00:00',
            'recurring': False,
        },
        headers=headers,
    )
    assert create_payment.status_code == 200
    created_payload = create_payment.json()
    assert created_payload['debt_id'] == debt_a.json()['id']

    bootstrap_after_create = client.get('/api/bootstrap', headers=headers)
    debts_after_create = {item['label']: item for item in bootstrap_after_create.json()['debts']}
    assert debts_after_create['Vehiculo']['balance_amount'] == 190000
    assert debts_after_create['Vehiculo']['balance_source'] == 'manual'

    update_payment = client.put(
        f"/api/transactions/{created_payload['id']}",
        json={
            'kind': 'deuda',
            'amount': 25000,
            'wallet': 'Banco',
            'category': 'Cooperativa',
            'fixed_income_source_id': None,
            'obligation_id': None,
            'credit_card_statement_id': None,
            'debt_id': debt_b.json()['id'],
            'tags': [],
            'notes': 'Reasignado',
            'date': '2026-08-25T12:00:00',
            'recurring': False,
        },
        headers=headers,
    )
    assert update_payment.status_code == 200

    bootstrap_after_update = client.get('/api/bootstrap', headers=headers)
    debts_after_update = {item['label']: item for item in bootstrap_after_update.json()['debts']}
    assert debts_after_update['Vehiculo']['balance_amount'] == 200000
    assert debts_after_update['Cooperativa']['balance_amount'] == 475000

    delete_payment = client.delete(f"/api/transactions/{created_payload['id']}", headers=headers)
    assert delete_payment.status_code == 204

    bootstrap_after_delete = client.get('/api/bootstrap', headers=headers)
    debts_after_delete = {item['label']: item for item in bootstrap_after_delete.json()['debts']}
    assert debts_after_delete['Vehiculo']['balance_amount'] == 200000
    assert debts_after_delete['Cooperativa']['balance_amount'] == 500000


def test_debt_priority_uses_interest_when_available() -> None:
    headers = ensure_app_headers('debtrate', '1234')
    debt_a = client.post(
        '/api/debts',
        json={
            'label': 'Vehiculo',
            'lender': 'Banco A',
            'balance_amount': 250000,
            'monthly_payment_amount': 15000,
            'currency': 'DOP',
            'payment_day': 12,
            'interest_rate_percent': 3.5,
            'interest_rate_period': 'monthly',
            'allow_extra_payment': True,
            'active': True,
            'notes': '',
        },
        headers=headers,
    )
    assert debt_a.status_code == 200
    debt_b = client.post(
        '/api/debts',
        json={
            'label': 'Personal',
            'lender': 'Banco B',
            'balance_amount': 300000,
            'monthly_payment_amount': 16000,
            'currency': 'DOP',
            'payment_day': 20,
            'interest_rate_percent': 18,
            'interest_rate_period': 'annual',
            'allow_extra_payment': True,
            'active': True,
            'notes': '',
        },
        headers=headers,
    )
    assert debt_b.status_code == 200

    dashboard = client.get('/api/bootstrap', headers=headers).json()['dashboard']
    assert dashboard['debt_priority_label'] == 'Vehiculo'
    assert 'tasa anual equivalente' in dashboard['debt_priority_reason']


def test_fixed_principal_debt_mode_exposes_operational_estimate() -> None:
    headers = ensure_app_headers('debtprincipal', '1234')

    response = client.post(
        '/api/debts',
        json={
            'label': 'Cooperativa garantia',
            'lender': 'Cooperativa',
            'balance_amount': 857785.88,
            'monthly_payment_amount': 21658.67,
            'currency': 'DOP',
            'payment_day': 17,
            'interest_rate_percent': None,
            'interest_rate_period': None,
            'amortization_mode': 'fixed_principal',
            'fixed_principal_payment_amount': 15998.33,
            'allow_extra_payment': True,
            'active': True,
            'notes': 'Capital fijo visible en estado de cuenta',
        },
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['amortization_mode'] == 'fixed_principal'
    assert payload['fixed_principal_payment_amount'] == 15998.33
    assert payload['estimated_next_balance_amount'] == 841787.55


def test_restricted_asset_is_visible_but_not_counted_as_income() -> None:
    headers = ensure_app_headers('guaranteeuser', '1234')

    setup = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Nomina base',
                    'amount': 10000,
                    'cadence': 'monthly',
                    'expected_day': 30,
                    'expected_weekday': None,
                    'wallet': 'Banco',
                    'active': True,
                }
            ],
            'obligations': [],
        },
        headers=headers,
    )
    assert setup.status_code == 200

    asset = client.post(
        '/api/restricted-assets',
        json={
            'label': 'Garantia cooperativa',
            'institution': 'Cooperativa',
            'balance_amount': 1000000,
            'currency': 'DOP',
            'availability_status': 'restricted',
            'linked_debt_id': None,
            'release_condition': 'Se libera al saldar el prestamo',
            'notes': 'Ahorro dado en garantia',
            'active': True,
        },
        headers=headers,
    )
    assert asset.status_code == 200

    bootstrap = client.get('/api/bootstrap', headers=headers)
    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert payload['dashboard']['restricted_assets_total'] == 1000000
    assert payload['dashboard']['available_restricted_assets_total'] == 0
    assert payload['dashboard']['income_reported_this_month'] == 0
    assert len(payload['restricted_assets']) == 1


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
    assert payload['dashboard']['free_margin_target'] == 17800
    assert payload['dashboard']['free_margin_available_now'] == 0
    assert payload['dashboard']['quincena_reserve_views'][1]['amount'] == 10000
    assert payload['dashboard']['quincena_reserve_views'][2]['amount'] == 10000


def test_linked_transactions_update_current_period_progress() -> None:
    headers = ensure_app_headers('linkedprogress', '1234')
    setup = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Nomina fija',
                    'amount': 1000,
                    'cadence': 'monthly',
                    'expected_day': 30,
                    'expected_weekday': None,
                    'wallet': 'Banco',
                    'active': True,
                }
            ],
            'obligations': [
                {
                    'label': 'Renta',
                    'amount': 800,
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
    assert setup.status_code == 200

    bootstrap = client.get('/api/bootstrap', headers=headers)
    payload = bootstrap.json()
    fixed_income_id = payload['fixed_income_sources'][0]['id']
    obligation_id = payload['obligations'][0]['id']

    income_tx = client.post(
        '/api/transactions',
        json={
            'kind': 'ingreso',
            'amount': 600,
            'wallet': 'Banco',
            'category': 'Nomina fija',
            'fixed_income_source_id': fixed_income_id,
            'obligation_id': None,
            'tags': [],
            'notes': 'Parcial de nomina',
            'date': '2026-08-13T10:00:00',
            'recurring': False,
        },
        headers=headers,
    )
    assert income_tx.status_code == 200

    expense_tx = client.post(
        '/api/transactions',
        json={
            'kind': 'gasto',
            'amount': 500,
            'wallet': 'Banco',
            'category': 'Casa',
            'fixed_income_source_id': None,
            'obligation_id': obligation_id,
            'tags': [],
            'notes': 'Abono de renta',
            'date': '2026-08-13T12:00:00',
            'recurring': False,
        },
        headers=headers,
    )
    assert expense_tx.status_code == 200

    refreshed = client.get('/api/bootstrap', headers=headers)
    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()
    fixed_income = refreshed_payload['fixed_income_sources'][0]
    obligation = refreshed_payload['obligations'][0]

    assert fixed_income['current_period_expected_amount'] == 1000
    assert fixed_income['current_period_recorded_amount'] == 600
    assert fixed_income['current_period_balance'] == 400
    assert obligation['current_period_expected_amount'] == 800
    assert obligation['current_period_recorded_amount'] == 500
    assert obligation['current_period_balance'] == 300
    assert obligation['current_period_status'] == 'Parcial'

    dashboard = refreshed_payload['dashboard']
    personal_bucket = next(item for item in dashboard['bucket_overviews'] if item['label'] == 'Personal blindado')

    assert dashboard['current_month_expense_total'] == 500
    assert dashboard['personal_spent_this_month'] == 0
    assert dashboard['fixed_cost_overflow'] == 500
    assert personal_bucket['total'] == 180
    assert dashboard['remaining_personal_recommended_this_month'] == 180
    assert dashboard['capitalization_target'] == 120
    assert personal_bucket['reserved'] == 0
    assert refreshed_payload['dashboard']['quincena_coverage'] == 0.625
    banco_wallet = next(item for item in dashboard['wallet_balances'] if item['label'] == 'Banco')
    assert banco_wallet['amount'] == 100
    assert banco_wallet['expected_income_amount'] == 1000
    assert banco_wallet['reported_income_amount'] == 600
    assert banco_wallet['pending_income_amount'] == 400


def test_expense_chart_includes_all_categories_instead_of_top_five() -> None:
    headers = ensure_app_headers('allcategories', '1234')
    setup = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Nomina base',
                    'amount': 70000,
                    'cadence': 'monthly',
                    'expected_day': 30,
                    'expected_weekday': None,
                    'wallet': 'Banco',
                    'active': True,
                }
            ],
            'obligations': [],
        },
        headers=headers,
    )
    assert setup.status_code == 200

    expense_rows = [
        ('Seguro V,', 18000),
        ('Nomina Mama', 10000),
        ('Manutencion', 8000),
        ('Personal', 5000),
        ('Compra', 4922),
        ('CENAS', 7568),
    ]

    for index, (category, amount) in enumerate(expense_rows, start=1):
        response = client.post(
            '/api/transactions',
            json={
                'kind': 'gasto',
                'amount': amount,
                'wallet': 'Banco',
                'category': category,
                'fixed_income_source_id': None,
                'obligation_id': None,
                'credit_card_statement_id': None,
                'tags': [],
                'notes': f'Gasto {category}',
                'date': f'2026-08-{index:02d}T10:00:00',
                'recurring': False,
            },
            headers=headers,
        )
        assert response.status_code == 200

    dashboard = client.get('/api/bootstrap', headers=headers).json()['dashboard']
    comparison_total = sum(item['current_amount'] for item in dashboard['expense_comparisons'])
    labels = {item['label'] for item in dashboard['expense_comparisons']}

    assert dashboard['current_month_expense_total'] == 53490
    assert comparison_total == 53490
    assert 'CENAS' in labels
    assert len(dashboard['expense_comparisons']) == 6


def test_category_and_tag_upsert_require_auth() -> None:
    headers = ensure_app_headers('cataloguser', '1234')
    category_response = client.post('/api/categories', json={'id': 'mascotas', 'label': 'Mascotas', 'scope': 'expense', 'type': 'Variable', 'color_token': 'plum', 'icon_token': 'favorite', 'active': True}, headers=headers)
    tag_response = client.post('/api/tags', json={'id': 'veterinaria', 'label': 'Veterinaria', 'color_token': 'sage', 'active': True}, headers=headers)

    assert category_response.status_code == 200
    assert category_response.json()['icon_token'] == 'favorite'
    assert tag_response.status_code == 200
    assert tag_response.json()['label'] == 'Veterinaria'


def test_tag_command_preset_roundtrip_in_bootstrap() -> None:
    headers = ensure_app_headers('tagcommand', '1234')
    create_tag = client.post(
        '/api/tags',
        json={
            'id': 'limpieza',
            'label': 'Limpieza',
            'color_token': 'terracotta',
            'active': True,
            'command_enabled': True,
            'preset_transaction_kind': 'gasto',
            'preset_fixed_income_source_id': None,
            'preset_obligation_id': 8,
            'preset_settlement_mode': 'partial',
            'preset_amount': 2000,
            'preset_wallet': 'Efectivo',
            'preset_category': 'Casa',
            'preset_recurring': False,
        },
        headers=headers,
    )

    assert create_tag.status_code == 200
    assert create_tag.json()['command_enabled'] is True
    assert create_tag.json()['preset_obligation_id'] == 8

    bootstrap = client.get('/api/bootstrap', headers=headers)
    assert bootstrap.status_code == 200

    tag = next(item for item in bootstrap.json()['tags'] if item['id'] == 'limpieza')
    assert tag['label'] == 'Limpieza'
    assert tag['preset_transaction_kind'] == 'gasto'
    assert tag['preset_settlement_mode'] == 'partial'
    assert tag['preset_amount'] == 2000
    assert tag['preset_wallet'] == 'Efectivo'
    assert tag['preset_category'] == 'Casa'


def test_credit_card_statement_payment_splits_fixed_and_personal() -> None:
    headers = ensure_app_headers('cardflow', '1234')
    setup = client.post(
        '/api/setup/complete',
        json={
            'fixed_income_sources': [
                {
                    'label': 'Nomina base',
                    'amount': 10000,
                    'cadence': 'monthly',
                    'expected_day': 30,
                    'expected_weekday': None,
                    'wallet': 'Banco',
                    'active': True,
                }
            ],
            'obligations': [
                {
                    'label': 'Internet',
                    'amount': 1800,
                    'category_id': 'casa',
                    'credit_card_id': None,
                    'cadence': 'monthly',
                    'due_day': 10,
                    'due_weekday': None,
                    'kind': 'Fija',
                    'status': 'Pendiente',
                },
                {
                    'label': 'Luz',
                    'amount': 1200,
                    'category_id': 'luz',
                    'credit_card_id': None,
                    'cadence': 'monthly',
                    'due_day': 12,
                    'due_weekday': None,
                    'kind': 'Fija',
                    'status': 'Pendiente',
                },
            ],
        },
        headers=headers,
    )
    assert setup.status_code == 200

    create_card = client.post(
        '/api/credit-cards',
        json={
            'label': 'Popular',
            'last4': '1100',
            'closing_day': 25,
            'due_day': 15,
            'limit_amount': 10000,
            'active': True,
        },
        headers=headers,
    )
    assert create_card.status_code == 200
    credit_card_id = create_card.json()['id']

    bootstrap = client.get('/api/bootstrap', headers=headers)
    payload = bootstrap.json()
    internet = next(item for item in payload['obligations'] if item['label'] == 'Internet')
    luz = next(item for item in payload['obligations'] if item['label'] == 'Luz')

    for obligation in (internet, luz):
        update_obligation = client.put(
            f"/api/obligations/{obligation['id']}",
            json={
                'label': obligation['label'],
                'amount': obligation['amount'],
                'category_id': obligation['category_id'],
                'credit_card_id': credit_card_id,
                'cadence': obligation['cadence'],
                'due_day': obligation['due_day'],
                'due_weekday': obligation['due_weekday'],
                'kind': obligation['kind'],
                'status': obligation['status'],
            },
            headers=headers,
        )
        assert update_obligation.status_code == 200

    now = datetime.now()
    due_date = (now + timedelta(days=2)).date().isoformat()
    statement = client.post(
        '/api/credit-card-statements',
        json={
            'credit_card_id': credit_card_id,
            'statement_date': now.date().isoformat(),
            'due_date': due_date,
            'period_year': now.year,
            'period_month': now.month,
            'statement_amount': 5000,
            'notes': 'Estado principal',
            'items': [
                {'obligation_id': internet['id'], 'amount': 1800},
                {'obligation_id': luz['id'], 'amount': 1200},
            ],
        },
        headers=headers,
    )
    assert statement.status_code == 200
    statement_id = statement.json()['id']

    before_payment = client.get('/api/bootstrap', headers=headers).json()
    assert before_payment['dashboard']['credit_card_alerts']
    assert before_payment['credit_card_statements'][0]['remaining_amount'] == 5000

    payment = client.post(
        '/api/transactions',
        json={
            'kind': 'gasto',
            'amount': 5000,
            'wallet': 'Banco',
            'category': 'Pago TC 1100',
            'fixed_income_source_id': None,
            'obligation_id': None,
            'credit_card_statement_id': statement_id,
            'tags': [],
            'notes': 'Pago total de la tarjeta',
            'date': now.replace(hour=11, minute=0, second=0, microsecond=0).isoformat(),
            'recurring': False,
        },
        headers=headers,
    )
    assert payment.status_code == 200

    refreshed = client.get('/api/bootstrap', headers=headers).json()
    refreshed_internet = next(item for item in refreshed['obligations'] if item['label'] == 'Internet')
    refreshed_luz = next(item for item in refreshed['obligations'] if item['label'] == 'Luz')
    statement_view = next(item for item in refreshed['credit_card_statements'] if item['id'] == statement_id)
    personal_bucket = next(item for item in refreshed['dashboard']['bucket_overviews'] if item['label'] == 'Personal blindado')

    assert refreshed_internet['current_period_recorded_amount'] == 1800
    assert refreshed_luz['current_period_recorded_amount'] == 1200
    assert statement_view['paid_amount'] == 5000
    assert statement_view['remaining_amount'] == 0
    assert statement_view['personal_paid_amount'] == 2000
    assert refreshed['dashboard']['personal_spent_this_month'] == 2000
    assert personal_bucket['reserved'] == 2000
    assert refreshed['dashboard']['credit_card_alerts'] == []


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