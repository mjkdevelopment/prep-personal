from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .database import Database
from .schemas import FlutterImportSummary


def import_flutter_database(source_path: str, target_database: Database, user_id: int, replace_existing: bool = True) -> FlutterImportSummary:
    if not Path(source_path).exists():
        raise FileNotFoundError(source_path)

    legacy_connection = sqlite3.connect(source_path)
    legacy_connection.row_factory = sqlite3.Row

    try:
        fixed_income_rows = _fetch_rows(legacy_connection, 'fixed_income_sources')
        obligation_rows = _fetch_rows(legacy_connection, 'obligations')
        transaction_rows = _fetch_rows(legacy_connection, 'transactions')
        meta_values = _load_meta_values(legacy_connection)
        categories = _decode_category_configs(meta_values.get('category_configs'))
        tags = _decode_tag_configs(meta_values.get('tag_configs'))
    finally:
        legacy_connection.close()

    with target_database.connect() as target_connection:
        if replace_existing:
            target_connection.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            target_connection.execute('DELETE FROM obligations WHERE user_id = ?', (user_id,))
            target_connection.execute('DELETE FROM fixed_income_sources WHERE user_id = ?', (user_id,))
            if categories:
                target_connection.execute('DELETE FROM categories WHERE user_id = ?', (user_id,))
            if tags:
                target_connection.execute('DELETE FROM tags WHERE user_id = ?', (user_id,))

        for row in fixed_income_rows:
            payload = {
                'label': row['label'],
                'amount': float(row['amount']),
                'cadence': row['cadence'] or 'monthly',
                'expected_day': int(row['expected_day']),
                'expected_weekday': row['expected_weekday'],
                'wallet': row['wallet'],
                'active': int(row['active'] or 0),
            }
            target_connection.execute('INSERT INTO fixed_income_sources(user_id, label, amount, cadence, expected_day, expected_weekday, wallet, active) VALUES(:user_id, :label, :amount, :cadence, :expected_day, :expected_weekday, :wallet, :active)', {'user_id': user_id, **payload})

        for row in obligation_rows:
            payload = {
                'label': row['label'],
                'amount': float(row['amount']),
                'category_id': row['category_id'],
                'cadence': row['cadence'] or 'monthly',
                'due_day': int(row['due_day']),
                'due_weekday': row['due_weekday'],
                'kind': row['kind'],
                'status': row['status'],
            }
            target_connection.execute('INSERT INTO obligations(user_id, label, amount, category_id, cadence, due_day, due_weekday, kind, status) VALUES(:user_id, :label, :amount, :category_id, :cadence, :due_day, :due_weekday, :kind, :status)', {'user_id': user_id, **payload})

        for row in transaction_rows:
            payload = {
                'kind': row['kind'],
                'amount': float(row['amount']),
                'wallet': row['wallet'],
                'category': row['category'],
                'tags_json': json.dumps(_decode_tags(row)),
                'notes': row['notes'] or '',
                'date_iso': row['date_iso'],
                'recurring': int(row['recurring'] or 0),
            }
            target_connection.execute('INSERT INTO transactions(user_id, kind, amount, wallet, category, tags_json, notes, date_iso, recurring) VALUES(:user_id, :kind, :amount, :wallet, :category, :tags_json, :notes, :date_iso, :recurring)', {'user_id': user_id, **payload})

        for item in categories:
            target_connection.execute('INSERT INTO categories(user_id, id, label, scope, type, color_token, icon_token, active) VALUES(:user_id, :id, :label, :scope, :type, :color_token, :icon_token, :active)', {'user_id': user_id, **item})

        for item in tags:
            target_connection.execute('INSERT INTO tags(user_id, id, label, color_token, active) VALUES(:user_id, :id, :label, :color_token, :active)', {'user_id': user_id, **item})

    return FlutterImportSummary(
        fixed_income_sources=len(fixed_income_rows),
        obligations=len(obligation_rows),
        transactions=len(transaction_rows),
        categories=len(categories),
        tags=len(tags),
        replace_existing=replace_existing,
    )


def _fetch_rows(connection: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]:
    if not _table_exists(connection, table_name):
        return []
    return connection.execute(f'SELECT * FROM {table_name}').fetchall()


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)).fetchone()
    return row is not None


def _load_meta_values(connection: sqlite3.Connection) -> dict[str, str]:
    if not _table_exists(connection, 'app_meta'):
        return {}
    rows = connection.execute('SELECT key, value FROM app_meta').fetchall()
    return {str(row['key']): str(row['value']) for row in rows}


def _decode_category_configs(raw_value: str | None) -> list[dict[str, object]]:
    if not raw_value:
        return []
    items = json.loads(raw_value)
    return [
        {
            'id': str(item['id']),
            'label': str(item['label']),
            'scope': str(item.get('scope') or 'expense'),
            'type': str(item.get('type') or 'Variable'),
            'color_token': str(item.get('colorToken') or 'gold'),
            'icon_token': str(item.get('iconToken') or 'receipt'),
            'active': 1 if item.get('active', True) else 0,
        }
        for item in items
        if isinstance(item, dict) and item.get('id') and item.get('label')
    ]


def _decode_tag_configs(raw_value: str | None) -> list[dict[str, object]]:
    if not raw_value:
        return []
    items = json.loads(raw_value)
    return [
        {
            'id': str(item['id']),
            'label': str(item['label']),
            'color_token': str(item.get('colorToken') or 'gold'),
            'active': 1 if item.get('active', True) else 0,
            'command_enabled': 1 if item.get('commandEnabled', False) else 0,
            'preset_transaction_kind': item.get('presetTransactionKind'),
            'preset_fixed_income_source_id': item.get('presetFixedIncomeSourceId'),
            'preset_obligation_id': item.get('presetObligationId'),
            'preset_settlement_mode': item.get('presetSettlementMode'),
            'preset_amount': item.get('presetAmount'),
            'preset_wallet': item.get('presetWallet'),
            'preset_category': item.get('presetCategory'),
            'preset_recurring': None if item.get('presetRecurring') is None else (1 if item.get('presetRecurring') else 0),
        }
        for item in items
        if isinstance(item, dict) and item.get('id') and item.get('label')
    ]


def _decode_tags(row: sqlite3.Row) -> list[str]:
    if 'tags_json' in row.keys() and row['tags_json']:
        return [str(item) for item in json.loads(row['tags_json'])]
    raw_tags = row['tags'] if 'tags' in row.keys() else ''
    return [item for item in str(raw_tags).split('|') if item]