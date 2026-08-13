from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .defaults import DEFAULT_CATEGORIES, DEFAULT_TAGS
from .schemas import AuditEvent, CategoryConfig, FixedIncomeSource, Obligation, TagConfig, Transaction, UserRole, UserSummary


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
            connection.execute('CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at_iso TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, password_salt TEXT NOT NULL, theme_id TEXT NOT NULL, setup_complete INTEGER NOT NULL, is_admin INTEGER NOT NULL, created_at_iso TEXT NOT NULL, updated_at_iso TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS trusted_sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER, device_name TEXT NOT NULL, created_at_iso TEXT NOT NULL, last_used_at_iso TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT, actor_user_id INTEGER, actor_username TEXT NOT NULL, action TEXT NOT NULL, target_type TEXT NOT NULL, target_value TEXT NOT NULL, detail TEXT NOT NULL, created_at_iso TEXT NOT NULL)')

            self._ensure_column(connection, 'fixed_income_sources', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'obligations', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'transactions', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'trusted_sessions', 'user_id', 'INTEGER')
            self._ensure_column(connection, 'users', 'theme_id', "TEXT NOT NULL DEFAULT 'emerald_editorial'")
            self._ensure_column(connection, 'users', 'setup_complete', 'INTEGER NOT NULL DEFAULT 0')
            self._ensure_column(connection, 'users', 'is_admin', 'INTEGER NOT NULL DEFAULT 0')
            self._ensure_column(connection, 'users', 'role', "TEXT NOT NULL DEFAULT 'operator'")
            self._ensure_column(connection, 'users', 'active', 'INTEGER NOT NULL DEFAULT 1')
            self._ensure_column(connection, 'users', 'created_by_user_id', 'INTEGER')
            self._ensure_user_scoped_categories_table(connection)
            self._ensure_user_scoped_tags_table(connection)
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
        if not raw_username or not raw_password:
            raise RuntimeError('OWNER_BOOTSTRAP_USERNAME y OWNER_BOOTSTRAP_PASSWORD deben configurarse juntos.')

        normalized_username = self._normalize_username(raw_username)
        if len(raw_password) < 4:
            raise RuntimeError('OWNER_BOOTSTRAP_PASSWORD debe tener al menos 4 caracteres.')

        with self.connect() as connection:
            owner_count = connection.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'owner'").fetchone()['total']
            if owner_count > 0:
                return False

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
        return [self._fixed_income(row) for row in rows]

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
            connection.execute('DELETE FROM fixed_income_sources WHERE id = ? AND user_id = ?', (item_id, user_id))

    def list_obligations(self, user_id: int) -> list[Obligation]:
        with self.connect() as connection:
            rows = connection.execute('SELECT * FROM obligations WHERE user_id = ? ORDER BY cadence ASC, due_weekday ASC, due_day ASC, id ASC', (user_id,)).fetchall()
        return [self._obligation(row) for row in rows]

    def create_obligation(self, user_id: int, payload: dict) -> Obligation:
        with self.connect() as connection:
            cursor = connection.execute(
                'INSERT INTO obligations(user_id, label, amount, category_id, cadence, due_day, due_weekday, kind, status) VALUES(:user_id, :label, :amount, :category_id, :cadence, :due_day, :due_weekday, :kind, :status)',
                {**payload, 'user_id': user_id},
            )
            row = connection.execute('SELECT * FROM obligations WHERE id = ? AND user_id = ?', (cursor.lastrowid, user_id)).fetchone()
        return self._obligation(row)

    def update_obligation(self, user_id: int, item_id: int, payload: dict) -> Obligation:
        with self.connect() as connection:
            connection.execute(
                'UPDATE obligations SET label = :label, amount = :amount, category_id = :category_id, cadence = :cadence, due_day = :due_day, due_weekday = :due_weekday, kind = :kind, status = :status WHERE id = :id AND user_id = :user_id',
                {**payload, 'id': item_id, 'user_id': user_id},
            )
            row = connection.execute('SELECT * FROM obligations WHERE id = ? AND user_id = ?', (item_id, user_id)).fetchone()
        if row is None:
            raise ValueError('Obligation not found')
        return self._obligation(row)

    def delete_obligation(self, user_id: int, item_id: int) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM obligations WHERE id = ? AND user_id = ?', (item_id, user_id))

    def list_transactions(self, user_id: int) -> list[Transaction]:
        with self.connect() as connection:
            rows = connection.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date_iso DESC, id DESC', (user_id,)).fetchall()
        return [self._transaction(row) for row in rows]

    def create_transaction(self, user_id: int, payload: dict) -> Transaction:
        with self.connect() as connection:
            cursor = connection.execute(
                'INSERT INTO transactions(user_id, kind, amount, wallet, category, tags_json, notes, date_iso, recurring) VALUES(:user_id, :kind, :amount, :wallet, :category, :tags_json, :notes, :date_iso, :recurring)',
                {**payload, 'user_id': user_id, 'tags_json': json.dumps(payload['tags']), 'date_iso': payload['date'].isoformat(), 'recurring': 1 if payload['recurring'] else 0},
            )
            row = connection.execute('SELECT * FROM transactions WHERE id = ? AND user_id = ?', (cursor.lastrowid, user_id)).fetchone()
        return self._transaction(row)

    def update_transaction(self, user_id: int, item_id: int, payload: dict) -> Transaction:
        with self.connect() as connection:
            connection.execute(
                'UPDATE transactions SET kind = :kind, amount = :amount, wallet = :wallet, category = :category, tags_json = :tags_json, notes = :notes, date_iso = :date_iso, recurring = :recurring WHERE id = :id AND user_id = :user_id',
                {**payload, 'tags_json': json.dumps(payload['tags']), 'date_iso': payload['date'].isoformat(), 'recurring': 1 if payload['recurring'] else 0, 'id': item_id, 'user_id': user_id},
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
                    'INSERT INTO obligations(user_id, label, amount, category_id, cadence, due_day, due_weekday, kind, status) VALUES(:user_id, :label, :amount, :category_id, :cadence, :due_day, :due_weekday, :kind, :status)',
                    {**payload, 'user_id': user_id},
                )
            connection.execute('UPDATE users SET setup_complete = 1, updated_at_iso = ? WHERE id = ?', (datetime.now().isoformat(), user_id))

    def reset_financial_setup(self, user_id: int) -> None:
        with self.connect() as connection:
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
            rows = connection.execute('SELECT id, label, color_token, active FROM tags WHERE user_id = ? ORDER BY label ASC', (user_id,)).fetchall()
        return [TagConfig(id=row['id'], label=row['label'], color_token=row['color_token'], active=bool(row['active'])) for row in rows]

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
                'INSERT INTO tags(user_id, id, label, color_token, active) VALUES(:user_id, :id, :label, :color_token, :active) ON CONFLICT(user_id, id) DO UPDATE SET label = excluded.label, color_token = excluded.color_token, active = excluded.active',
                {**payload, 'user_id': user_id, 'active': 1 if payload['active'] else 0},
            )
            row = connection.execute('SELECT id, label, color_token, active FROM tags WHERE user_id = ? AND id = ?', (user_id, payload['id'])).fetchone()
        return TagConfig(id=row['id'], label=row['label'], color_token=row['color_token'], active=bool(row['active']))

    def delete_category(self, user_id: int, category_id: str) -> None:
        with self.connect() as connection:
            connection.execute('UPDATE obligations SET category_id = NULL WHERE user_id = ? AND category_id = ?', (user_id, category_id))
            connection.execute('DELETE FROM categories WHERE user_id = ? AND id = ?', (user_id, category_id))

    def delete_tag(self, user_id: int, tag_id: str) -> None:
        with self.connect() as connection:
            connection.execute('DELETE FROM tags WHERE user_id = ? AND id = ?', (user_id, tag_id))

    @staticmethod
    def _fixed_income(row: sqlite3.Row) -> FixedIncomeSource:
        return FixedIncomeSource(id=row['id'], label=row['label'], amount=row['amount'], cadence=row['cadence'], expected_day=row['expected_day'], expected_weekday=row['expected_weekday'], wallet=row['wallet'], active=bool(row['active']))

    @staticmethod
    def _obligation(row: sqlite3.Row) -> Obligation:
        return Obligation(id=row['id'], label=row['label'], amount=row['amount'], category_id=row['category_id'], cadence=row['cadence'], due_day=row['due_day'], due_weekday=row['due_weekday'], kind=row['kind'], status=row['status'])

    @staticmethod
    def _transaction(row: sqlite3.Row) -> Transaction:
        return Transaction(id=row['id'], kind=row['kind'], amount=row['amount'], wallet=row['wallet'], category=row['category'], tags=json.loads(row['tags_json']), notes=row['notes'], date=datetime.fromisoformat(row['date_iso']), recurring=bool(row['recurring']))

    @staticmethod
    def _normalize_username(username: str) -> str:
        normalized = username.strip().lower()
        if len(normalized) < 3:
            raise ValueError('El usuario debe tener al menos 3 caracteres.')
        return normalized

    @staticmethod
    def _default_db_path() -> str:
        if any(name.startswith('RAILWAY_') for name in os.environ):
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
