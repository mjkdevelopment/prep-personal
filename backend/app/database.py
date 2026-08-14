from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import calendar
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .defaults import DEFAULT_CATEGORIES, DEFAULT_TAGS
from .schemas import AuditEvent, CategoryConfig, CreditCard, CreditCardStatement, CreditCardStatementItem, FixedIncomeSource, Obligation, TagConfig, Transaction, UserRole, UserSummary


@dataclass
class UserRecord:
    id: int
    username: str
    role: UserRole
    active: bool
    theme_id: str
    setup_complete: bool

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.owner

    @property
    def can_manage_users(self) -> bool:
        return self.role == UserRole.owner and self.active

    @property
    def can_edit_data(self) -> bool:
        return self.role in {UserRole.admin, UserRole.operator} and self.active


class Database:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv('APP_DB_PATH', self._default_db_path())
        self.startup_warning: str | None = None
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @property
    def bootstrap_code_path(self) -> str:
        return str(Path(self.db_path).with_name('admin_bootstrap_code.txt'))

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS fixed_income_sources(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, label TEXT NOT NULL, amount REAL NOT NULL, cadence TEXT NOT NULL, expected_day INTEGER NOT NULL, expected_weekday INTEGER, wallet TEXT NOT NULL, active INTEGER NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS obligations(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, label TEXT NOT NULL, amount REAL NOT NULL, category_id TEXT, cadence TEXT NOT NULL, due_day INTEGER NOT NULL, due_weekday INTEGER, kind TEXT NOT NULL, status TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT NOT NULL, amount REAL NOT NULL, wallet TEXT NOT NULL, category TEXT NOT NULL, tags_json TEXT NOT NULL, notes TEXT NOT NULL, date_iso TEXT NOT NULL, recurring INTEGER NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS credit_cards(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, label TEXT NOT NULL, last4 TEXT NOT NULL, closing_day INTEGER NOT NULL, due_day INTEGER NOT NULL, limit_amount REAL NOT NULL, active INTEGER NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS credit_card_statements(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, credit_card_id INTEGER NOT NULL, statement_date_iso TEXT NOT NULL, due_date_iso TEXT NOT NULL, period_year INTEGER NOT NULL, period_month INTEGER NOT NULL, statement_amount REAL NOT NULL, notes TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS credit_card_statement_items(id INTEGER PRIMARY KEY AUTOINCREMENT, statement_id INTEGER NOT NULL, obligation_id INTEGER NOT NULL, amount REAL NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at_iso TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, password_salt TEXT NOT NULL, theme_id TEXT NOT NULL, setup_complete INTEGER NOT NULL, is_admin INTEGER NOT NULL, created_at_iso TEXT NOT NULL, updated_at_iso TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS trusted_sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER, device_name TEXT NOT NULL, created_at_iso TEXT NOT NULL, last_used_at_iso TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT, actor_user_id INTEGER, actor_username TEXT NOT NULL, action TEXT NOT NULL, target_type TEXT NOT NULL, target_value TEXT NOT NULL, detail TEXT NOT NULL, created_at_iso TEXT NOT NULL)')

            self._ensure_column(connection, 'fixed_income_sources', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'obligations', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'obligations', 'credit_card_id', 'INTEGER')
            self._ensure_column(connection, 'transactions', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'transactions', 'fixed_income_source_id', 'INTEGER')
            self._ensure_column(connection, 'transactions', 'obligation_id', 'INTEGER')
            self._ensure_column(connection, 'transactions', 'credit_card_statement_id', 'INTEGER')
            self._ensure_column(connection, 'trusted_sessions', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'users', 'theme_id', "TEXT NOT NULL DEFAULT 'emerald_editorial'")
            self._ensure_column(connection, 'users', 'setup_complete', 'INTEGER NOT NULL DEFAULT 0')
            self._ensure_column(connection, 'users', 'is_admin', 'INTEGER NOT NULL DEFAULT 0')
            self._ensure_column(connection, 'users', 'role', "TEXT NOT NULL DEFAULT 'operator'")
            self._ensure_column(connection, 'users', 'active', 'INTEGER NOT NULL DEFAULT 1')
            self._ensure_column(connection, 'users', 'created_by_user_id', 'INTEGER')
            self._ensure_user_scoped_categories_table(connection)
            self._ensure_user_scoped_tags_table(connection)
            self._ensure_column(connection, 'tags', 'command_enabled', 'INTEGER NOT NULL DEFAULT 0')
            self._ensure_column(connection, 'tags', 'preset_transaction_kind', 'TEXT')
            self._ensure_column(connection, 'tags', 'preset_fixed_income_source_id', 'INTEGER')
            self._ensure_column(connection, 'tags', 'preset_obligation_id', 'INTEGER')
            self._ensure_column(connection, 'tags', 'preset_settlement_mode', 'TEXT')
            self._ensure_column(connection, 'tags', 'preset_amount', 'REAL')
            self._ensure_column(connection, 'tags', 'preset_wallet', 'TEXT')
            self._ensure_column(connection, 'tags', 'preset_category', 'TEXT')
            self._ensure_column(connection, 'tags', 'preset_recurring', 'INTEGER')
            connection.execute("UPDATE users SET role = CASE WHEN is_admin = 1 THEN 'owner' ELSE 'operator' END WHERE role IS NULL OR role = '' OR role NOT IN ('owner', 'admin', 'operator', 'viewer')")
            connection.execute("UPDATE users SET is_admin = CASE WHEN role = 'owner' THEN 1 ELSE 0 END")
            connection.execute('UPDATE users SET active = 1 WHERE active IS NULL')

            if self._get_meta_value(connection, 'setup_complete') is None:
                connection.execute(
                    'INSERT INTO app_meta(key, value, updated_at_iso) VALUES(?, ?, ?)',
                    ('setup_complete', 'true' if self._has_residual_financial_data(connection) else 'false', datetime.now().isoformat()),
                )
            self._ensure_bootstrap_code(connection)

    def auto_bootstrap_owner_from_env(self) -> bool:
        raw_username = os.getenv('OWNER_BOOTSTRAP_USERNAME', '').strip()
        raw_password = os.getenv('OWNER_BOOTSTRAP_PASSWORD', '').strip()

        if not raw_username and not raw_password:
            return False

        with self.connect() as connection:
            owner_count = connection.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'owner'").fetchone()['total']
            if owner_count > 0:
                return False

            if not raw_username or not raw_password:
                raise RuntimeError('OWNER_BOOTSTRAP_USERNAME y OWNER_BOOTSTRAP_PASSWORD deben configurarse juntos.')

            normalized_username = self._normalize_username(raw_username)
            if len(raw_password) < 4:
                raise RuntimeError('OWNER_BOOTSTRAP_PASSWORD debe tener al menos 4 caracteres.')

            existing_user = connection.execute('SELECT id FROM users WHERE username = ? LIMIT 1', (normalized_username,)).fetchone()
            if existing_user is not None:
                raise RuntimeError('OWNER_BOOTSTRAP_USERNAME ya existe en la base actual.')

            theme_id = os.getenv('OWNER_BOOTSTRAP_THEME_ID', '').strip() or self._get_meta_value(connection, 'theme_id') or 'emerald_editorial'
            setup_complete = self._get_meta_value(connection, 'setup_complete') == 'true' or self._has_residual_financial_data(connection)
            user_id = self._insert_user(connection, normalized_username, raw_password, UserRole.owner, theme_id, setup_complete, None)
            self._claim_orphaned_records(connection, user_id)
            self._ensure_default_catalogs(connection, user_id)
            self._set_meta_value(connection, 'admin_bootstrap_code', '')
            Path(self.bootstrap_code_path).unlink(missing_ok=True)
            self._insert_audit_event(connection, actor_user_id=user_id, actor_username=normalized_username, action='bootstrap_owner_env', target_type='user', target_value=normalized_username, detail='Cuenta owner inicial creada automaticamente por variables de entorno.')
        return True

    def has_users(self) -> bool:
        with self.connect() as connection:
            row = connection.execute('SELECT COUNT(*) AS total FROM users').fetchone()
            return bool(row and row['total'] > 0)

    def has_owner(self) -> bool:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'owner'").fetchone()
            return bool(row and row['total'] > 0)

    def list_users(self) -> list[UserSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT users.id, users.username, users.role, users.active, creators.username AS created_by_username FROM users LEFT JOIN users AS creators ON creators.id = users.created_by_user_id ORDER BY CASE users.role WHEN \"admin\" THEN 0 WHEN \"operator\" THEN 1 ELSE 2 END, users.username ASC'
            ).fetchall()
        return [UserSummary(id=row['id'], username=row['username'], role=row['role'], active=bool(row['active']), created_by_username=row['created_by_username']) for row in rows]

    def list_owner_panel_users(self) -> list[UserSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT users.id, users.username, users.role, users.active, creators.username AS created_by_username FROM users LEFT JOIN users AS creators ON creators.id = users.created_by_user_id ORDER BY CASE users.role WHEN \"owner\" THEN 0 WHEN \"admin\" THEN 1 WHEN \"operator\" THEN 2 ELSE 3 END, users.username ASC'
            ).fetchall()
        return [UserSummary(id=row['id'], username=row['username'], role=row['role'], active=bool(row['active']), created_by_username=row['created_by_username']) for row in rows]

    def list_audit_events(self, limit: int = 24) -> list[AuditEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT id, actor_username, action, target_type, target_value, detail, created_at_iso FROM audit_events ORDER BY id DESC LIMIT ?',
                (limit,),
            ).fetchall()
        return [AuditEvent(id=row['id'], actor_username=row['actor_username'], action=row['action'], target_type=row['target_type'], target_value=row['target_value'], detail=row['detail'], created_at_iso=row['created_at_iso']) for row in rows]

    def authenticate_user(self, username: str, password: str) -> UserRecord:
        normalized_username = self._normalize_username(username)
        with self.connect() as connection:
            row = connection.execute('SELECT * FROM users WHERE username = ? LIMIT 1', (normalized_username,)).fetchone()
            if row is not None:
                if not secrets.compare_digest(row['password_hash'], self._hash_password(password, row['password_salt'])):
                    raise ValueError('Credenciales invalidas.')
                if not bool(row['active']):
                    raise ValueError('Esta cuenta esta desactivada.')
                return self._user_record(row)
        raise ValueError('Credenciales invalidas.')

    def authenticate_owner(self, username: str, password: str) -> UserRecord:
        user = self.authenticate_user(username, password)
        if not user.is_owner:
            raise ValueError('Esta cuenta no usa el panel owner.')
        return user

    def authenticate_app_user(self, username: str, password: str) -> UserRecord:
        user = self.authenticate_user(username, password)
        if user.is_owner:
            raise ValueError('La cuenta owner entra desde /owner.')
        return user

    def admin_bootstrap_required(self) -> bool:
        return not self.has_owner()

    def bootstrap_owner(self, username: str, password: str, bootstrap_code: str) -> UserRecord:
        normalized_username = self._normalize_username(username)
        with self.connect() as connection:
            owner_count = connection.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'owner'").fetchone()['total']
            if owner_count > 0:
                raise ValueError('El usuario administrador inicial ya fue creado.')

            existing_user = connection.execute('SELECT id FROM users WHERE username = ? LIMIT 1', (normalized_username,)).fetchone()
            if existing_user is not None:
                raise ValueError('Ese usuario ya existe. Usa otro nombre para la cuenta owner.')

            expected_code = self._get_meta_value(connection, 'admin_bootstrap_code')
            if not expected_code or not secrets.compare_digest(expected_code, bootstrap_code.strip()):
                raise ValueError('Codigo de bootstrap invalido.')

            legacy_hash = self._get_meta_value(connection, 'password_hash')
            legacy_salt = self._get_meta_value(connection, 'password_salt')
            if legacy_hash and legacy_salt:
                if not secrets.compare_digest(legacy_hash, self._hash_password(password, legacy_salt)):
                    raise ValueError('Debes usar la contrasena ya configurada para reclamar esta base.')

            theme_id = self._get_meta_value(connection, 'theme_id') or 'emerald_editorial'
            setup_complete = self._get_meta_value(connection, 'setup_complete') == 'true' or self._has_residual_financial_data(connection)
            user_id = self._insert_user(connection, normalized_username, password, UserRole.owner, theme_id, setup_complete, None)
            self._claim_orphaned_records(connection, user_id)
            self._ensure_default_catalogs(connection, user_id)
            self._set_meta_value(connection, 'admin_bootstrap_code', '')
            Path(self.bootstrap_code_path).unlink(missing_ok=True)
            self._insert_audit_event(connection, actor_user_id=user_id, actor_username=normalized_username, action='bootstrap_owner', target_type='user', target_value=normalized_username, detail='Cuenta owner inicial creada.')
            created = connection.execute('SELECT * FROM users WHERE id = ? LIMIT 1', (user_id,)).fetchone()
        if created is None:
            raise ValueError('No se pudo crear el usuario inicial.')
        return self._user_record(created)

    def create_user(self, actor: UserRecord, username: str, password: str, role: UserRole = UserRole.operator) -> UserSummary:
        normalized_username = self._normalize_username(username)
        if role == UserRole.owner:
            raise ValueError('La cuenta owner solo se crea en el bootstrap inicial.')
        with self.connect() as connection:
            existing = connection.execute('SELECT id FROM users WHERE username = ? LIMIT 1', (normalized_username,)).fetchone()
            if existing is not None:
                raise ValueError('Ese usuario ya existe.')
            user_id = self._insert_user(connection, normalized_username, password, role, 'emerald_editorial', False, actor.id)
            self._ensure_default_catalogs(connection, user_id)
            self._insert_audit_event(connection, actor_user_id=actor.id, actor_username=actor.username, action='create_user', target_type='user', target_value=normalized_username, detail=f'Rol inicial: {role}.')
            row = connection.execute('SELECT username FROM users WHERE id = ? LIMIT 1', (actor.id,)).fetchone()
        return UserSummary(id=user_id, username=normalized_username, role=role, active=True, created_by_username=row['username'] if row else actor.username)

    def update_user_access(self, actor: UserRecord, user_id: int, role: UserRole, active: bool) -> UserSummary:
        if actor.id == user_id and not active:
            raise ValueError('No puedes desactivar tu propia cuenta.')
        if role == UserRole.owner:
            raise ValueError('El rol owner no se asigna desde el panel.')
        with self.connect() as connection:
            target = connection.execute('SELECT id, username FROM users WHERE id = ? LIMIT 1', (user_id,)).fetchone()
            if target is None:
                raise ValueError('Usuario no encontrado.')
            current_target = connection.execute('SELECT role, active FROM users WHERE id = ? LIMIT 1', (user_id,)).fetchone()
            if current_target and current_target['role'] == UserRole.owner.value:
                raise ValueError('La cuenta owner no se modifica desde este panel.')
            connection.execute('UPDATE users SET role = ?, is_admin = 0, active = ?, updated_at_iso = ? WHERE id = ?', (role.value, 1 if active else 0, datetime.now().isoformat(), user_id))
            self._insert_audit_event(connection, actor_user_id=actor.id, actor_username=actor.username, action='update_user_access', target_type='user', target_value=str(target['username']), detail=f'Rol: {role}. Activo: {"si" if active else "no"}.')
            row = connection.execute(
                'SELECT users.id, users.username, users.role, users.active, creators.username AS created_by_username FROM users LEFT JOIN users AS creators ON creators.id = users.created_by_user_id WHERE users.id = ? LIMIT 1',
                (user_id,),
            ).fetchone()
            if not active:
                connection.execute('DELETE FROM trusted_sessions WHERE user_id = ?', (user_id,))
        return UserSummary(id=row['id'], username=row['username'], role=row['role'], active=bool(row['active']), created_by_username=row['created_by_username'])

    def delete_user(self, actor: UserRecord, user_id: int) -> None:
        if actor.id == user_id:
            raise ValueError('No puedes eliminar tu propia cuenta owner.')
        with self.connect() as connection:
            target = connection.execute('SELECT username, role FROM users WHERE id = ? LIMIT 1', (user_id,)).fetchone()
            if target is None:
                raise ValueError('Usuario no encontrado.')
            if target['role'] == UserRole.owner.value:
                raise ValueError('La cuenta owner no se puede eliminar.')
            connection.execute('DELETE FROM trusted_sessions WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM fixed_income_sources WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM obligations WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM categories WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM tags WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM users WHERE id = ?', (user_id,))
            self._insert_audit_event(connection, actor_user_id=actor.id, actor_username=actor.username, action='delete_user', target_type='user', target_value=str(target['username']), detail='Cuenta eliminada desde panel owner.')

    def get_session_user(self, token: str | None) -> UserRecord | None:
        if not token:
            return None
        token_hash = self._hash_token(token)
        with self.connect() as connection:
            row = connection.execute(
                'SELECT users.* FROM trusted_sessions JOIN users ON users.id = trusted_sessions.user_id WHERE trusted_sessions.token_hash = ? LIMIT 1',
                (token_hash,),
            ).fetchone()
            if row is None:
                return None
            if not bool(row['active']):
                connection.execute('DELETE FROM trusted_sessions WHERE token_hash = ?', (token_hash,))
                return None
            connection.execute('UPDATE trusted_sessions SET last_used_at_iso = ? WHERE token_hash = ?', (datetime.now().isoformat(), token_hash))
            return self._user_record(row)

    def create_session(self, user_id: int, device_name: str) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        now = datetime.now().isoformat()
        with self.connect() as connection:
            connection.execute(
                'INSERT INTO trusted_sessions(token_hash, user_id, device_name, created_at_iso, last_used_at_iso) VALUES(?, ?, ?, ?, ?)',
                (token_hash, user_id, device_name, now, now),
            )
        return token

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        token_hash = self._hash_token(token)
        with self.connect() as connection:
            connection.execute('DELETE FROM trusted_sessions WHERE token_hash = ?', (token_hash,))

    def revoke_all_sessions(self, user_id: int | None = None) -> None:
        with self.connect() as connection:
            if user_id is None:
                connection.execute('DELETE FROM trusted_sessions')
            else:
                connection.execute('DELETE FROM trusted_sessions WHERE user_id = ?', (user_id,))

    def verify_password(self, user_id: int, password: str) -> bool:
        with self.connect() as connection:
            row = connection.execute('SELECT password_hash, password_salt FROM users WHERE id = ? LIMIT 1', (user_id,)).fetchone()
            if row is None:
                return False
            candidate_hash = self._hash_password(password, row['password_salt'])
            return secrets.compare_digest(row['password_hash'], candidate_hash)

    def set_password(self, user_id: int, password: str) -> None:
        with self.connect() as connection:
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            connection.execute(
                'UPDATE users SET password_salt = ?, password_hash = ?, updated_at_iso = ? WHERE id = ?',
                (salt, password_hash, datetime.now().isoformat(), user_id),
            )

    def record_audit(self, actor: UserRecord, action: str, target_type: str, target_value: str, detail: str) -> None:
        with self.connect() as connection:
            self._insert_audit_event(connection, actor_user_id=actor.id, actor_username=actor.username, action=action, target_type=target_type, target_value=target_value, detail=detail)

    def is_setup_complete(self, user_id: int) -> bool:
        with self.connect() as connection:
            row = connection.execute('SELECT setup_complete FROM users WHERE id = ? LIMIT 1', (user_id,)).fetchone()
            return bool(row and row['setup_complete'])

    def set_setup_complete(self, user_id: int, value: bool) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE users SET setup_complete = ?, updated_at_iso = ? WHERE id = ?', (1 if value else 0, datetime.now().isoformat(), user_id))

    def get_theme_id(self, user_id: int) -> str:
        with self.connect() as connection:
            row = connection.execute('SELECT theme_id FROM users WHERE id = ? LIMIT 1', (user_id,)).fetchone()
            return str(row['theme_id']) if row and row['theme_id'] else 'emerald_editorial'

    def set_theme_id(self, user_id: int, theme_id: str) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE users SET theme_id = ?, updated_at_iso = ? WHERE id = ?', (theme_id, datetime.now().isoformat(), user_id))

    def list_fixed_income_sources(self, user_id: int) -> list[FixedIncomeSource]:
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT * FROM fixed_income_sources WHERE user_id = ? ORDER BY cadence ASC, expected_weekday ASC, expected_day ASC, id ASC',
                (user_id,),
            ).fetchall()
            progress = self._current_period_totals(connection, user_id, 'fixed_income_source_id', 'ingreso')
        return [self._fixed_income(row, progress.get(row['id'], 0)) for row in rows]

    def create_fixed_income_source(self, user_id: int, payload: dict) -> FixedIncomeSource:
        with self.connect() as connection:
            cursor = connection.execute(
                'INSERT INTO fixed_income_sources(user_id, label, amount, cadence, expected_day, expected_weekday, wallet, active) VALUES(:user_id, :label, :amount, :cadence, :expected_day, :expected_weekday, :wallet, :active)',
                {**payload, 'user_id': user_id, 'active': 1 if payload['active'] else 0},
            )
            row = connection.execute('SELECT * FROM fixed_income_sources WHERE id = ? AND user_id = ?', (cursor.lastrowid, user_id)).fetchone()
        return self._fixed_income(row)

    def update_fixed_income_source(self, user_id: int, item_id: int, payload: dict) -> FixedIncomeSource:
        with self.connect() as connection:
            connection.execute(
                'UPDATE fixed_income_sources SET label = :label, amount = :amount, cadence = :cadence, expected_day = :expected_day, expected_weekday = :expected_weekday, wallet = :wallet, active = :active WHERE id = :id AND user_id = :user_id',
                {**payload, 'active': 1 if payload['active'] else 0, 'id': item_id, 'user_id': user_id},
            )
            row = connection.execute('SELECT * FROM fixed_income_sources WHERE id = ? AND user_id = ?', (item_id, user_id)).fetchone()
        if row is None:
            raise ValueError('Fixed income source not found')
        return self._fixed_income(row)

    def delete_fixed_income_source(self, user_id: int, item_id: int) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE transactions SET fixed_income_source_id = NULL WHERE user_id = ? AND fixed_income_source_id = ?', (user_id, item_id))
            connection.execute('DELETE FROM fixed_income_sources WHERE id = ? AND user_id = ?', (item_id, user_id))

    def list_obligations(self, user_id: int) -> list[Obligation]:
        with self.connect() as connection:
            rows = connection.execute('SELECT * FROM obligations WHERE user_id = ? ORDER BY cadence ASC, due_weekday ASC, due_day ASC, id ASC', (user_id,)).fetchall()
            progress = self._current_period_totals(connection, user_id, 'obligation_id', 'gasto')
            statement_progress = self._current_period_credit_card_obligation_totals(connection, user_id)
        return [self._obligation(row, progress.get(row['id'], 0) + statement_progress.get(row['id'], 0)) for row in rows]

    def create_obligation(self, user_id: int, payload: dict) -> Obligation:
        with self.connect() as connection:
            cursor = connection.execute(
                'INSERT INTO obligations(user_id, label, amount, category_id, credit_card_id, cadence, due_day, due_weekday, kind, status) VALUES(:user_id, :label, :amount, :category_id, :credit_card_id, :cadence, :due_day, :due_weekday, :kind, :status)',
                {**payload, 'user_id': user_id},
            )
            row = connection.execute('SELECT * FROM obligations WHERE id = ? AND user_id = ?', (cursor.lastrowid, user_id)).fetchone()
        return self._obligation(row)

    def update_obligation(self, user_id: int, item_id: int, payload: dict) -> Obligation:
        with self.connect() as connection:
            connection.execute(
                'UPDATE obligations SET label = :label, amount = :amount, category_id = :category_id, credit_card_id = :credit_card_id, cadence = :cadence, due_day = :due_day, due_weekday = :due_weekday, kind = :kind, status = :status WHERE id = :id AND user_id = :user_id',
                {**payload, 'id': item_id, 'user_id': user_id},
            )
            row = connection.execute('SELECT * FROM obligations WHERE id = ? AND user_id = ?', (item_id, user_id)).fetchone()
        if row is None:
            raise ValueError('Obligation not found')
        return self._obligation(row)

    def delete_obligation(self, user_id: int, item_id: int) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM credit_card_statement_items WHERE obligation_id = ? AND statement_id IN (SELECT id FROM credit_card_statements WHERE user_id = ?)', (item_id, user_id))
            connection.execute('UPDATE transactions SET obligation_id = NULL WHERE user_id = ? AND obligation_id = ?', (user_id, item_id))
            connection.execute('DELETE FROM obligations WHERE id = ? AND user_id = ?', (item_id, user_id))

    def list_credit_cards(self, user_id: int) -> list[CreditCard]:
        with self.connect() as connection:
            rows = connection.execute('SELECT * FROM credit_cards WHERE user_id = ? ORDER BY label ASC, last4 ASC', (user_id,)).fetchall()
        return [CreditCard(id=row['id'], label=row['label'], last4=row['last4'], closing_day=row['closing_day'], due_day=row['due_day'], limit_amount=row['limit_amount'], active=bool(row['active'])) for row in rows]

    def create_credit_card(self, user_id: int, payload: dict) -> CreditCard:
        with self.connect() as connection:
            cursor = connection.execute(
                'INSERT INTO credit_cards(user_id, label, last4, closing_day, due_day, limit_amount, active) VALUES(:user_id, :label, :last4, :closing_day, :due_day, :limit_amount, :active)',
                {**payload, 'user_id': user_id, 'active': 1 if payload['active'] else 0},
            )
            row = connection.execute('SELECT * FROM credit_cards WHERE id = ? AND user_id = ?', (cursor.lastrowid, user_id)).fetchone()
        return CreditCard(id=row['id'], label=row['label'], last4=row['last4'], closing_day=row['closing_day'], due_day=row['due_day'], limit_amount=row['limit_amount'], active=bool(row['active']))

    def update_credit_card(self, user_id: int, item_id: int, payload: dict) -> CreditCard:
        with self.connect() as connection:
            connection.execute(
                'UPDATE credit_cards SET label = :label, last4 = :last4, closing_day = :closing_day, due_day = :due_day, limit_amount = :limit_amount, active = :active WHERE id = :id AND user_id = :user_id',
                {**payload, 'id': item_id, 'user_id': user_id, 'active': 1 if payload['active'] else 0},
            )
            row = connection.execute('SELECT * FROM credit_cards WHERE id = ? AND user_id = ?', (item_id, user_id)).fetchone()
        if row is None:
            raise ValueError('Tarjeta no encontrada.')
        return CreditCard(id=row['id'], label=row['label'], last4=row['last4'], closing_day=row['closing_day'], due_day=row['due_day'], limit_amount=row['limit_amount'], active=bool(row['active']))

    def delete_credit_card(self, user_id: int, item_id: int) -> None:
        with self.connect() as connection:
            statement_rows = connection.execute('SELECT id FROM credit_card_statements WHERE user_id = ? AND credit_card_id = ?', (user_id, item_id)).fetchall()
            statement_ids = [int(row['id']) for row in statement_rows]
            if statement_ids:
                placeholders = ','.join('?' for _ in statement_ids)
                connection.execute(f'UPDATE transactions SET credit_card_statement_id = NULL WHERE user_id = ? AND credit_card_statement_id IN ({placeholders})', (user_id, *statement_ids))
                connection.execute(f'DELETE FROM credit_card_statement_items WHERE statement_id IN ({placeholders})', tuple(statement_ids))
                connection.execute(f'DELETE FROM credit_card_statements WHERE id IN ({placeholders}) AND user_id = ?', (*statement_ids, user_id))
            connection.execute('UPDATE obligations SET credit_card_id = NULL WHERE user_id = ? AND credit_card_id = ?', (user_id, item_id))
            connection.execute('DELETE FROM credit_cards WHERE id = ? AND user_id = ?', (item_id, user_id))

    def list_credit_card_statements(self, user_id: int) -> list[CreditCardStatement]:
        with self.connect() as connection:
            statement_rows = connection.execute(
                'SELECT statements.*, cards.label AS card_label, cards.last4 AS card_last4, cards.limit_amount AS card_limit_amount FROM credit_card_statements AS statements JOIN credit_cards AS cards ON cards.id = statements.credit_card_id WHERE statements.user_id = ? ORDER BY statements.due_date_iso ASC, statements.id ASC',
                (user_id,),
            ).fetchall()
            item_rows = connection.execute(
                'SELECT items.statement_id, items.obligation_id, items.amount, obligations.label AS obligation_label FROM credit_card_statement_items AS items JOIN obligations ON obligations.id = items.obligation_id WHERE items.statement_id IN (SELECT id FROM credit_card_statements WHERE user_id = ?) ORDER BY items.id ASC',
                (user_id,),
            ).fetchall()
            payment_rows = connection.execute(
                'SELECT id, credit_card_statement_id, amount, date_iso FROM transactions WHERE user_id = ? AND credit_card_statement_id IS NOT NULL AND kind = ? ORDER BY date_iso ASC, id ASC',
                (user_id, 'gasto'),
            ).fetchall()
        return self._credit_card_statements_from_rows(statement_rows, item_rows, payment_rows)

    def create_credit_card_statement(self, user_id: int, payload: dict) -> CreditCardStatement:
        with self.connect() as connection:
            card = connection.execute('SELECT id FROM credit_cards WHERE id = ? AND user_id = ? LIMIT 1', (payload['credit_card_id'], user_id)).fetchone()
            if card is None:
                raise ValueError('Tarjeta no encontrada.')
            cursor = connection.execute(
                'INSERT INTO credit_card_statements(user_id, credit_card_id, statement_date_iso, due_date_iso, period_year, period_month, statement_amount, notes) VALUES(:user_id, :credit_card_id, :statement_date_iso, :due_date_iso, :period_year, :period_month, :statement_amount, :notes)',
                {
                    'user_id': user_id,
                    'credit_card_id': payload['credit_card_id'],
                    'statement_date_iso': payload['statement_date'].isoformat(),
                    'due_date_iso': payload['due_date'].isoformat(),
                    'period_year': payload['period_year'],
                    'period_month': payload['period_month'],
                    'statement_amount': payload['statement_amount'],
                    'notes': payload.get('notes', ''),
                },
            )
            for item in payload.get('items', []):
                obligation = connection.execute('SELECT id FROM obligations WHERE id = ? AND user_id = ? LIMIT 1', (item['obligation_id'], user_id)).fetchone()
                if obligation is None:
                    raise ValueError('Obligacion no encontrada para el estado de cuenta.')
                connection.execute('INSERT INTO credit_card_statement_items(statement_id, obligation_id, amount) VALUES(?, ?, ?)', (cursor.lastrowid, item['obligation_id'], item['amount']))
        return self.list_credit_card_statements(user_id)[-1]

    def update_credit_card_statement(self, user_id: int, item_id: int, payload: dict) -> CreditCardStatement:
        with self.connect() as connection:
            existing = connection.execute('SELECT id FROM credit_card_statements WHERE id = ? AND user_id = ? LIMIT 1', (item_id, user_id)).fetchone()
            if existing is None:
                raise ValueError('Estado de cuenta no encontrado.')
            card = connection.execute('SELECT id FROM credit_cards WHERE id = ? AND user_id = ? LIMIT 1', (payload['credit_card_id'], user_id)).fetchone()
            if card is None:
                raise ValueError('Tarjeta no encontrada.')
            connection.execute(
                'UPDATE credit_card_statements SET credit_card_id = :credit_card_id, statement_date_iso = :statement_date_iso, due_date_iso = :due_date_iso, period_year = :period_year, period_month = :period_month, statement_amount = :statement_amount, notes = :notes WHERE id = :id AND user_id = :user_id',
                {
                    'id': item_id,
                    'user_id': user_id,
                    'credit_card_id': payload['credit_card_id'],
                    'statement_date_iso': payload['statement_date'].isoformat(),
                    'due_date_iso': payload['due_date'].isoformat(),
                    'period_year': payload['period_year'],
                    'period_month': payload['period_month'],
                    'statement_amount': payload['statement_amount'],
                    'notes': payload.get('notes', ''),
                },
            )
            connection.execute('DELETE FROM credit_card_statement_items WHERE statement_id = ?', (item_id,))
            for statement_item in payload.get('items', []):
                obligation = connection.execute('SELECT id FROM obligations WHERE id = ? AND user_id = ? LIMIT 1', (statement_item['obligation_id'], user_id)).fetchone()
                if obligation is None:
                    raise ValueError('Obligacion no encontrada para el estado de cuenta.')
                connection.execute('INSERT INTO credit_card_statement_items(statement_id, obligation_id, amount) VALUES(?, ?, ?)', (item_id, statement_item['obligation_id'], statement_item['amount']))
        statements = self.list_credit_card_statements(user_id)
        statement = next((item for item in statements if item.id == item_id), None)
        if statement is None:
            raise ValueError('Estado de cuenta no encontrado.')
        return statement

    def delete_credit_card_statement(self, user_id: int, item_id: int) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE transactions SET credit_card_statement_id = NULL WHERE user_id = ? AND credit_card_statement_id = ?', (user_id, item_id))
            connection.execute('DELETE FROM credit_card_statement_items WHERE statement_id = ?', (item_id,))
            connection.execute('DELETE FROM credit_card_statements WHERE id = ? AND user_id = ?', (item_id, user_id))

    def list_transactions(self, user_id: int) -> list[Transaction]:
        with self.connect() as connection:
            rows = connection.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date_iso DESC, id DESC', (user_id,)).fetchall()
        return [self._transaction(row) for row in rows]

    def create_transaction(self, user_id: int, payload: dict) -> Transaction:
        with self.connect() as connection:
            normalized = self._normalize_transaction_payload(connection, user_id, payload)
            cursor = connection.execute(
                'INSERT INTO transactions(user_id, kind, amount, wallet, category, fixed_income_source_id, obligation_id, credit_card_statement_id, tags_json, notes, date_iso, recurring) VALUES(:user_id, :kind, :amount, :wallet, :category, :fixed_income_source_id, :obligation_id, :credit_card_statement_id, :tags_json, :notes, :date_iso, :recurring)',
                {**normalized, 'user_id': user_id, 'tags_json': json.dumps(normalized['tags']), 'date_iso': normalized['date'].isoformat(), 'recurring': 1 if normalized['recurring'] else 0},
            )
            row = connection.execute('SELECT * FROM transactions WHERE id = ? AND user_id = ?', (cursor.lastrowid, user_id)).fetchone()
        return self._transaction(row)

    def update_transaction(self, user_id: int, item_id: int, payload: dict) -> Transaction:
        with self.connect() as connection:
            normalized = self._normalize_transaction_payload(connection, user_id, payload)
            connection.execute(
                'UPDATE transactions SET kind = :kind, amount = :amount, wallet = :wallet, category = :category, fixed_income_source_id = :fixed_income_source_id, obligation_id = :obligation_id, credit_card_statement_id = :credit_card_statement_id, tags_json = :tags_json, notes = :notes, date_iso = :date_iso, recurring = :recurring WHERE id = :id AND user_id = :user_id',
                {**normalized, 'tags_json': json.dumps(normalized['tags']), 'date_iso': normalized['date'].isoformat(), 'recurring': 1 if normalized['recurring'] else 0, 'id': item_id, 'user_id': user_id},
            )
            row = connection.execute('SELECT * FROM transactions WHERE id = ? AND user_id = ?', (item_id, user_id)).fetchone()
        if row is None:
            raise ValueError('Transaction not found')
        return self._transaction(row)

    def delete_transaction(self, user_id: int, item_id: int) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (item_id, user_id))

    def replace_fixed_income_sources(self, user_id: int, items: list[dict]) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM fixed_income_sources WHERE user_id = ?', (user_id,))
            for payload in items:
                connection.execute(
                    'INSERT INTO fixed_income_sources(user_id, label, amount, cadence, expected_day, expected_weekday, wallet, active) VALUES(:user_id, :label, :amount, :cadence, :expected_day, :expected_weekday, :wallet, :active)',
                    {**payload, 'user_id': user_id, 'active': 1 if payload['active'] else 0},
                )

    def replace_obligations(self, user_id: int, items: list[dict]) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM obligations WHERE user_id = ?', (user_id,))
            for payload in items:
                connection.execute(
                    'INSERT INTO obligations(user_id, label, amount, category_id, cadence, due_day, due_weekday, kind, status) VALUES(:user_id, :label, :amount, :category_id, :cadence, :due_day, :due_weekday, :kind, :status)',
                    {**payload, 'user_id': user_id},
                )

    def clear_transactions(self, user_id: int) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))

    def complete_initial_setup(self, user_id: int, fixed_income_sources: list[dict], obligations: list[dict]) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM credit_card_statement_items WHERE statement_id IN (SELECT id FROM credit_card_statements WHERE user_id = ?)', (user_id,))
            connection.execute('DELETE FROM credit_card_statements WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM credit_cards WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM fixed_income_sources WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM obligations WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            for payload in fixed_income_sources:
                connection.execute(
                    'INSERT INTO fixed_income_sources(user_id, label, amount, cadence, expected_day, expected_weekday, wallet, active) VALUES(:user_id, :label, :amount, :cadence, :expected_day, :expected_weekday, :wallet, :active)',
                    {**payload, 'user_id': user_id, 'active': 1 if payload['active'] else 0},
                )
            for payload in obligations:
                connection.execute(
                    'INSERT INTO obligations(user_id, label, amount, category_id, credit_card_id, cadence, due_day, due_weekday, kind, status) VALUES(:user_id, :label, :amount, :category_id, :credit_card_id, :cadence, :due_day, :due_weekday, :kind, :status)',
                    {**payload, 'user_id': user_id},
                )
            connection.execute('UPDATE users SET setup_complete = 1, updated_at_iso = ? WHERE id = ?', (datetime.now().isoformat(), user_id))

    def reset_financial_setup(self, user_id: int) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM credit_card_statement_items WHERE statement_id IN (SELECT id FROM credit_card_statements WHERE user_id = ?)', (user_id,))
            connection.execute('DELETE FROM credit_card_statements WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM credit_cards WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM obligations WHERE user_id = ?', (user_id,))
            connection.execute('DELETE FROM fixed_income_sources WHERE user_id = ?', (user_id,))
            connection.execute('UPDATE users SET setup_complete = 0, updated_at_iso = ? WHERE id = ?', (datetime.now().isoformat(), user_id))

    def list_categories(self, user_id: int) -> list[CategoryConfig]:
        with self.connect() as connection:
            self._ensure_default_catalogs(connection, user_id)
            rows = connection.execute('SELECT id, label, scope, type, color_token, icon_token, active FROM categories WHERE user_id = ? ORDER BY scope ASC, label ASC', (user_id,)).fetchall()
        return [CategoryConfig(id=row['id'], label=row['label'], scope=row['scope'], type=row['type'], color_token=row['color_token'], icon_token=row['icon_token'], active=bool(row['active'])) for row in rows]

    def list_tags(self, user_id: int) -> list[TagConfig]:
        with self.connect() as connection:
            self._ensure_default_catalogs(connection, user_id)
            rows = connection.execute('SELECT * FROM tags WHERE user_id = ? ORDER BY label ASC', (user_id,)).fetchall()
        return [self._tag(row) for row in rows]

    def upsert_category(self, user_id: int, payload: dict) -> CategoryConfig:
        with self.connect() as connection:
            connection.execute(
                'INSERT INTO categories(user_id, id, label, scope, type, color_token, icon_token, active) VALUES(:user_id, :id, :label, :scope, :type, :color_token, :icon_token, :active) ON CONFLICT(user_id, id) DO UPDATE SET label = excluded.label, scope = excluded.scope, type = excluded.type, color_token = excluded.color_token, icon_token = excluded.icon_token, active = excluded.active',
                {**payload, 'user_id': user_id, 'active': 1 if payload['active'] else 0},
            )
            row = connection.execute('SELECT id, label, scope, type, color_token, icon_token, active FROM categories WHERE user_id = ? AND id = ?', (user_id, payload['id'])).fetchone()
        return CategoryConfig(id=row['id'], label=row['label'], scope=row['scope'], type=row['type'], color_token=row['color_token'], icon_token=row['icon_token'], active=bool(row['active']))

    def upsert_tag(self, user_id: int, payload: dict) -> TagConfig:
        with self.connect() as connection:
            connection.execute(
                'INSERT INTO tags(user_id, id, label, color_token, active, command_enabled, preset_transaction_kind, preset_fixed_income_source_id, preset_obligation_id, preset_settlement_mode, preset_amount, preset_wallet, preset_category, preset_recurring) VALUES(:user_id, :id, :label, :color_token, :active, :command_enabled, :preset_transaction_kind, :preset_fixed_income_source_id, :preset_obligation_id, :preset_settlement_mode, :preset_amount, :preset_wallet, :preset_category, :preset_recurring) ON CONFLICT(user_id, id) DO UPDATE SET label = excluded.label, color_token = excluded.color_token, active = excluded.active, command_enabled = excluded.command_enabled, preset_transaction_kind = excluded.preset_transaction_kind, preset_fixed_income_source_id = excluded.preset_fixed_income_source_id, preset_obligation_id = excluded.preset_obligation_id, preset_settlement_mode = excluded.preset_settlement_mode, preset_amount = excluded.preset_amount, preset_wallet = excluded.preset_wallet, preset_category = excluded.preset_category, preset_recurring = excluded.preset_recurring',
                {
                    **payload,
                    'user_id': user_id,
                    'active': 1 if payload['active'] else 0,
                    'command_enabled': 1 if payload.get('command_enabled') else 0,
                    'preset_recurring': None if payload.get('preset_recurring') is None else (1 if payload.get('preset_recurring') else 0),
                },
            )
            row = connection.execute('SELECT * FROM tags WHERE user_id = ? AND id = ?', (user_id, payload['id'])).fetchone()
        return self._tag(row)

    def delete_category(self, user_id: int, category_id: str) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE obligations SET category_id = NULL WHERE user_id = ? AND category_id = ?', (user_id, category_id))
            connection.execute('DELETE FROM categories WHERE user_id = ? AND id = ?', (user_id, category_id))

    def delete_tag(self, user_id: int, tag_id: str) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM tags WHERE user_id = ? AND id = ?', (user_id, tag_id))

    def _current_period_totals(self, connection: sqlite3.Connection, user_id: int, column: str, kind: str) -> dict[int, float]:
        start_iso, end_iso = self._current_period_bounds()
        rows = connection.execute(
            f'SELECT {column} AS linked_id, SUM(amount) AS total FROM transactions WHERE user_id = ? AND kind = ? AND {column} IS NOT NULL AND date_iso >= ? AND date_iso < ? GROUP BY {column}',
            (user_id, kind, start_iso, end_iso),
        ).fetchall()
        return {int(row['linked_id']): float(row['total'] or 0) for row in rows}

    def _current_period_credit_card_obligation_totals(self, connection: sqlite3.Connection, user_id: int) -> dict[int, float]:
        now = datetime.now()
        statement_rows = connection.execute(
            'SELECT statements.*, cards.label AS card_label, cards.last4 AS card_last4, cards.limit_amount AS card_limit_amount FROM credit_card_statements AS statements JOIN credit_cards AS cards ON cards.id = statements.credit_card_id WHERE statements.user_id = ? AND statements.period_year = ? AND statements.period_month = ? ORDER BY statements.id ASC',
            (user_id, now.year, now.month),
        ).fetchall()
        if not statement_rows:
            return {}
        statement_ids = [int(row['id']) for row in statement_rows]
        placeholders = ','.join('?' for _ in statement_ids)
        item_rows = connection.execute(
            f'SELECT items.statement_id, items.obligation_id, items.amount, obligations.label AS obligation_label FROM credit_card_statement_items AS items JOIN obligations ON obligations.id = items.obligation_id WHERE items.statement_id IN ({placeholders}) ORDER BY items.id ASC',
            tuple(statement_ids),
        ).fetchall()
        payment_rows = connection.execute(
            f'SELECT id, credit_card_statement_id, amount, date_iso FROM transactions WHERE user_id = ? AND credit_card_statement_id IN ({placeholders}) AND kind = ? ORDER BY date_iso ASC, id ASC',
            (user_id, *statement_ids, 'gasto'),
        ).fetchall()
        totals: dict[int, float] = {}
        for statement in self._credit_card_statements_from_rows(statement_rows, item_rows, payment_rows):
            _, _, _, obligation_paid = self._statement_payment_breakdown(statement.items, payment_rows, statement.id)
            for obligation_id, amount in obligation_paid.items():
                totals[obligation_id] = totals.get(obligation_id, 0) + amount
        return totals

    @staticmethod
    def _current_period_bounds() -> tuple[str, str]:
        now = datetime.now()
        start = datetime(now.year, now.month, 1)
        next_month = datetime(now.year + (1 if now.month == 12 else 0), 1 if now.month == 12 else now.month + 1, 1)
        return start.isoformat(), next_month.isoformat()

    @staticmethod
    def _period_status(recorded_amount: float, expected_amount: float) -> str:
        if expected_amount <= 0:
            return 'Cubierto'
        if recorded_amount <= 0:
            return 'Pendiente'
        if recorded_amount >= expected_amount:
            return 'Cubierto'
        return 'Parcial'

    def _normalize_transaction_payload(self, connection: sqlite3.Connection, user_id: int, payload: dict) -> dict:
        normalized = dict(payload)
        fixed_income_source_id = normalized.get('fixed_income_source_id')
        obligation_id = normalized.get('obligation_id')
        credit_card_statement_id = normalized.get('credit_card_statement_id')
        linked_targets = [value for value in (fixed_income_source_id, obligation_id, credit_card_statement_id) if value is not None]
        if len(linked_targets) > 1:
            raise ValueError('Un movimiento solo puede vincularse a una fuente fija, una obligacion o un estado de tarjeta a la vez.')
        if fixed_income_source_id is not None:
            if normalized['kind'] != 'ingreso':
                raise ValueError('Solo un ingreso puede vincularse a un ingreso fijo.')
            row = connection.execute('SELECT id FROM fixed_income_sources WHERE id = ? AND user_id = ? LIMIT 1', (fixed_income_source_id, user_id)).fetchone()
            if row is None:
                raise ValueError('Ingreso fijo no encontrado.')
        if obligation_id is not None:
            if normalized['kind'] != 'gasto':
                raise ValueError('Solo un gasto puede vincularse a una obligacion.')
            row = connection.execute('SELECT id FROM obligations WHERE id = ? AND user_id = ? LIMIT 1', (obligation_id, user_id)).fetchone()
            if row is None:
                raise ValueError('Obligacion no encontrada.')
        if credit_card_statement_id is not None:
            if normalized['kind'] != 'gasto':
                raise ValueError('Solo un gasto puede vincularse a un estado de tarjeta.')
            row = connection.execute('SELECT id FROM credit_card_statements WHERE id = ? AND user_id = ? LIMIT 1', (credit_card_statement_id, user_id)).fetchone()
            if row is None:
                raise ValueError('Estado de cuenta no encontrado.')
        return normalized

    @staticmethod
    def _fixed_income(row: sqlite3.Row, recorded_amount: float = 0) -> FixedIncomeSource:
        expected_amount = float(row['amount']) * {'weekly': 4, 'biweekly': 2}.get(row['cadence'], 1)
        settled_amount = min(max(recorded_amount, 0), expected_amount)
        return FixedIncomeSource(id=row['id'], label=row['label'], amount=row['amount'], cadence=row['cadence'], expected_day=row['expected_day'], expected_weekday=row['expected_weekday'], wallet=row['wallet'], active=bool(row['active']), current_period_expected_amount=expected_amount, current_period_recorded_amount=settled_amount, current_period_balance=max(expected_amount - settled_amount, 0))

    def _obligation(self, row: sqlite3.Row, recorded_amount: float = 0) -> Obligation:
        expected_amount = float(row['amount']) * {'weekly': 4, 'biweekly': 2}.get(row['cadence'], 1)
        settled_amount = min(max(recorded_amount, 0), expected_amount)
        return Obligation(id=row['id'], label=row['label'], amount=row['amount'], category_id=row['category_id'], credit_card_id=row['credit_card_id'], cadence=row['cadence'], due_day=row['due_day'], due_weekday=row['due_weekday'], kind=row['kind'], status=row['status'], current_period_expected_amount=expected_amount, current_period_recorded_amount=settled_amount, current_period_balance=max(expected_amount - settled_amount, 0), current_period_status=self._period_status(settled_amount, expected_amount))

    @staticmethod
    def _transaction(row: sqlite3.Row) -> Transaction:
        return Transaction(id=row['id'], kind=row['kind'], amount=row['amount'], wallet=row['wallet'], category=row['category'], fixed_income_source_id=row['fixed_income_source_id'], obligation_id=row['obligation_id'], credit_card_statement_id=row['credit_card_statement_id'], tags=json.loads(row['tags_json']), notes=row['notes'], date=datetime.fromisoformat(row['date_iso']), recurring=bool(row['recurring']))

    def _credit_card_statements_from_rows(self, statement_rows: list[sqlite3.Row], item_rows: list[sqlite3.Row], payment_rows: list[sqlite3.Row]) -> list[CreditCardStatement]:
        items_by_statement: dict[int, list[CreditCardStatementItem]] = {}
        for row in item_rows:
            items_by_statement.setdefault(int(row['statement_id']), []).append(CreditCardStatementItem(obligation_id=int(row['obligation_id']), obligation_label=str(row['obligation_label']), amount=float(row['amount'])))

        statements: list[CreditCardStatement] = []
        for row in statement_rows:
            statement_id = int(row['id'])
            items = items_by_statement.get(statement_id, [])
            fixed_paid_amount, personal_paid_amount, _, _ = self._statement_payment_breakdown(items, payment_rows, statement_id)
            paid_amount = sum(float(payment['amount']) for payment in payment_rows if int(payment['credit_card_statement_id']) == statement_id)
            remaining_amount = max(float(row['statement_amount']) - paid_amount, 0)
            payment_status = 'Pagado' if remaining_amount <= 0 else 'Parcial' if paid_amount > 0 else 'Pendiente'
            statements.append(
                CreditCardStatement(
                    id=statement_id,
                    credit_card_id=int(row['credit_card_id']),
                    statement_date=datetime.fromisoformat(str(row['statement_date_iso'])).date(),
                    due_date=datetime.fromisoformat(str(row['due_date_iso'])).date(),
                    period_year=int(row['period_year']),
                    period_month=int(row['period_month']),
                    statement_amount=float(row['statement_amount']),
                    notes=str(row['notes'] or ''),
                    card_label=str(row['card_label']),
                    card_last4=str(row['card_last4']),
                    paid_amount=paid_amount,
                    remaining_amount=remaining_amount,
                    fixed_items_total=sum(item.amount for item in items),
                    fixed_items_paid_amount=fixed_paid_amount,
                    personal_paid_amount=personal_paid_amount,
                    payment_status=payment_status,
                    utilization_ratio=0 if not float(row['card_limit_amount'] or 0) else float(row['statement_amount']) / float(row['card_limit_amount']),
                    items=items,
                )
            )
        return statements

    @staticmethod
    def _statement_payment_breakdown(items: list[CreditCardStatementItem], payment_rows: list[sqlite3.Row], statement_id: int) -> tuple[float, float, dict[int, float], dict[int, float]]:
        relevant_payments = [row for row in payment_rows if int(row['credit_card_statement_id']) == statement_id]
        remaining_fixed_total = sum(item.amount for item in items)
        fixed_paid_amount = 0.0
        personal_paid_amount = 0.0
        personal_by_transaction: dict[int, float] = {}
        for payment in relevant_payments:
            amount = float(payment['amount'])
            fixed_portion = min(amount, max(remaining_fixed_total, 0))
            remaining_fixed_total = max(remaining_fixed_total - fixed_portion, 0)
            fixed_paid_amount += fixed_portion
            personal_portion = max(amount - fixed_portion, 0)
            personal_paid_amount += personal_portion
            personal_by_transaction[int(payment['id'])] = personal_portion

        remaining_fixed_paid = fixed_paid_amount
        obligation_paid: dict[int, float] = {}
        for item in items:
            applied = min(item.amount, remaining_fixed_paid)
            if applied > 0:
                obligation_paid[item.obligation_id] = obligation_paid.get(item.obligation_id, 0) + applied
                remaining_fixed_paid -= applied
        return fixed_paid_amount, personal_paid_amount, personal_by_transaction, obligation_paid

    @staticmethod
    def _tag(row: sqlite3.Row) -> TagConfig:
        return TagConfig(
            id=row['id'],
            label=row['label'],
            color_token=row['color_token'],
            active=bool(row['active']),
            command_enabled=bool(row['command_enabled']),
            preset_transaction_kind=row['preset_transaction_kind'],
            preset_fixed_income_source_id=row['preset_fixed_income_source_id'],
            preset_obligation_id=row['preset_obligation_id'],
            preset_settlement_mode=row['preset_settlement_mode'],
            preset_amount=row['preset_amount'],
            preset_wallet=row['preset_wallet'],
            preset_category=row['preset_category'],
            preset_recurring=None if row['preset_recurring'] is None else bool(row['preset_recurring']),
        )

    @staticmethod
    def _normalize_username(username: str) -> str:
        normalized = username.strip().lower()
        if len(normalized) < 3:
            raise ValueError('El usuario debe tener al menos 3 caracteres.')
        return normalized

    @staticmethod
    def _default_db_path() -> str:
        data_dir = Path('/data')
        if any(name.startswith('RAILWAY_') for name in os.environ) or data_dir.is_dir():
            return '/data/gride_ledger.db'
        return 'backend/data/gride_ledger.db'

    @staticmethod
    def _user_record(row: sqlite3.Row) -> UserRecord:
        return UserRecord(
            id=int(row['id']),
            username=str(row['username']),
            role=UserRole(str(row['role']) if row['role'] else ('owner' if row['is_admin'] else 'operator')),
            active=bool(row['active']) if row['active'] is not None else True,
            theme_id=str(row['theme_id']),
            setup_complete=bool(row['setup_complete']),
        )

    def _insert_user(self, connection: sqlite3.Connection, username: str, password: str, role: UserRole, theme_id: str, setup_complete: bool, created_by_user_id: int | None) -> int:
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        now = datetime.now().isoformat()
        cursor = connection.execute(
            'INSERT INTO users(username, password_hash, password_salt, theme_id, setup_complete, is_admin, role, active, created_by_user_id, created_at_iso, updated_at_iso) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (username, password_hash, salt, theme_id, 1 if setup_complete else 0, 1 if role == UserRole.owner else 0, role.value, 1, created_by_user_id, now, now),
        )
        return int(cursor.lastrowid)

    @staticmethod
    def _insert_audit_event(connection: sqlite3.Connection, actor_user_id: int | None, actor_username: str, action: str, target_type: str, target_value: str, detail: str) -> None:
        connection.execute(
            'INSERT INTO audit_events(actor_user_id, actor_username, action, target_type, target_value, detail, created_at_iso) VALUES(?, ?, ?, ?, ?, ?, ?)',
            (actor_user_id, actor_username, action, target_type, target_value, detail, datetime.now().isoformat()),
        )

    def _ensure_default_catalogs(self, connection: sqlite3.Connection, user_id: int) -> None:
        category_count = connection.execute('SELECT COUNT(*) AS total FROM categories WHERE user_id = ?', (user_id,)).fetchone()['total']
        if category_count == 0:
            for category in DEFAULT_CATEGORIES:
                connection.execute(
                    'INSERT INTO categories(user_id, id, label, scope, type, color_token, icon_token, active) VALUES(:user_id, :id, :label, :scope, :type, :color_token, :icon_token, :active)',
                    {**category, 'user_id': user_id, 'active': 1},
                )

        tag_count = connection.execute('SELECT COUNT(*) AS total FROM tags WHERE user_id = ?', (user_id,)).fetchone()['total']
        if tag_count == 0:
            for tag in DEFAULT_TAGS:
                connection.execute(
                    'INSERT INTO tags(user_id, id, label, color_token, active) VALUES(:user_id, :id, :label, :color_token, :active)',
                    {**tag, 'user_id': user_id, 'active': 1},
                )

    def _claim_orphaned_records(self, connection: sqlite3.Connection, user_id: int) -> None:
        connection.execute('UPDATE fixed_income_sources SET user_id = ? WHERE user_id IS NULL', (user_id,))
        connection.execute('UPDATE obligations SET user_id = ? WHERE user_id IS NULL', (user_id,))
        connection.execute('UPDATE transactions SET user_id = ? WHERE user_id IS NULL', (user_id,))
        connection.execute('UPDATE categories SET user_id = ? WHERE user_id IS NULL', (user_id,))
        connection.execute('UPDATE tags SET user_id = ? WHERE user_id IS NULL', (user_id,))

    def _ensure_bootstrap_code(self, connection: sqlite3.Connection) -> None:
        owner_count = connection.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'owner'").fetchone()['total']
        existing_code = self._get_meta_value(connection, 'admin_bootstrap_code')
        if owner_count > 0:
            if existing_code:
                self._set_meta_value(connection, 'admin_bootstrap_code', '')
            Path(self.bootstrap_code_path).unlink(missing_ok=True)
            return
        if existing_code:
            if not Path(self.bootstrap_code_path).exists():
                Path(self.bootstrap_code_path).write_text(existing_code, encoding='utf-8')
            return
        bootstrap_code = secrets.token_urlsafe(12)
        self._set_meta_value(connection, 'admin_bootstrap_code', bootstrap_code)
        Path(self.bootstrap_code_path).write_text(bootstrap_code, encoding='utf-8')

    @staticmethod
    def _has_residual_financial_data(connection: sqlite3.Connection) -> bool:
        fixed_income_count = connection.execute('SELECT COUNT(*) FROM fixed_income_sources').fetchone()[0]
        obligation_count = connection.execute('SELECT COUNT(*) FROM obligations').fetchone()[0]
        transaction_count = connection.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
        return any(count > 0 for count in (fixed_income_count, obligation_count, transaction_count))

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        row = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)).fetchone()
        return row is not None

    @staticmethod
    def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f'PRAGMA table_info({table_name})').fetchall()
        return {str(row['name']) for row in rows}

    def _ensure_column(self, connection: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
        if not self._table_exists(connection, table_name):
            return
        if column_name in self._column_names(connection, table_name):
            return
        connection.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}')

    def _ensure_user_scoped_categories_table(self, connection: sqlite3.Connection) -> None:
        if not self._table_exists(connection, 'categories'):
            connection.execute('CREATE TABLE categories(row_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, id TEXT NOT NULL, label TEXT NOT NULL, scope TEXT NOT NULL, type TEXT NOT NULL, color_token TEXT NOT NULL, icon_token TEXT NOT NULL, active INTEGER NOT NULL, UNIQUE(user_id, id))')
            return

        columns = self._column_names(connection, 'categories')
        if 'user_id' in columns and 'row_id' in columns:
            return

        connection.execute('ALTER TABLE categories RENAME TO categories_legacy')
        connection.execute('CREATE TABLE categories(row_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, id TEXT NOT NULL, label TEXT NOT NULL, scope TEXT NOT NULL, type TEXT NOT NULL, color_token TEXT NOT NULL, icon_token TEXT NOT NULL, active INTEGER NOT NULL, UNIQUE(user_id, id))')
        connection.execute('INSERT INTO categories(user_id, id, label, scope, type, color_token, icon_token, active) SELECT NULL, id, label, scope, type, color_token, icon_token, active FROM categories_legacy')
        connection.execute('DROP TABLE categories_legacy')

    def _ensure_user_scoped_tags_table(self, connection: sqlite3.Connection) -> None:
        if not self._table_exists(connection, 'tags'):
            connection.execute('CREATE TABLE tags(row_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, id TEXT NOT NULL, label TEXT NOT NULL, color_token TEXT NOT NULL, active INTEGER NOT NULL, UNIQUE(user_id, id))')
            return

        columns = self._column_names(connection, 'tags')
        if 'user_id' in columns and 'row_id' in columns:
            return

        connection.execute('ALTER TABLE tags RENAME TO tags_legacy')
        connection.execute('CREATE TABLE tags(row_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, id TEXT NOT NULL, label TEXT NOT NULL, color_token TEXT NOT NULL, active INTEGER NOT NULL, UNIQUE(user_id, id))')
        connection.execute('INSERT INTO tags(user_id, id, label, color_token, active) SELECT NULL, id, label, color_token, active FROM tags_legacy')
        connection.execute('DROP TABLE tags_legacy')

    @staticmethod
    def _get_meta_value(connection: sqlite3.Connection, key: str) -> str | None:
        row = connection.execute('SELECT value FROM app_meta WHERE key = ? LIMIT 1', (key,)).fetchone()
        return None if row is None else str(row['value'])

    @staticmethod
    def _set_meta_value(connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute('INSERT INTO app_meta(key, value, updated_at_iso) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at_iso = excluded.updated_at_iso', (key, value, datetime.now().isoformat()))

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 200000).hex()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
