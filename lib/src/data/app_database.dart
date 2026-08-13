import 'dart:convert';

import 'package:path/path.dart' as path;
import 'package:sqflite/sqflite.dart';

import '../domain/models.dart';

class AppDatabase {
  AppDatabase({DatabaseFactory? databaseFactoryOverride, String? databasePathOverride})
      : _databaseFactory = databaseFactoryOverride,
        _databasePathOverride = databasePathOverride;

  static const int currentVersion = 5;
  static const String _databaseName = 'prep_personal.db';

  Database? _database;
  final DatabaseFactory? _databaseFactory;
  final String? _databasePathOverride;

  Future<void> initialize() async {
    _database ??= await _open();
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }

  Future<Database> get database async {
    if (_database == null) {
      await initialize();
    }

    return _database!;
  }

  Future<List<FixedIncomeSourceModel>> getFixedIncomeSources() async {
    final db = await database;
    final rows = await db.query(
      'fixed_income_sources',
      orderBy: 'cadence ASC, expected_weekday ASC, expected_day ASC, id ASC',
    );
    return rows.map(FixedIncomeSourceModel.fromMap).toList();
  }

  Future<bool> hasResidualFinancialData() async {
    final db = await database;
    final fixedIncomeCount = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM fixed_income_sources'),
    ) ??
        0;
    final obligationCount = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM obligations'),
    ) ??
        0;
    final transactionCount = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM transactions'),
    ) ??
        0;
    return fixedIncomeCount > 0 || obligationCount > 0 || transactionCount > 0;
  }

  Future<List<ObligationModel>> getObligations() async {
    final db = await database;
    final rows = await db.query(
      'obligations',
      orderBy: 'cadence ASC, due_weekday ASC, due_day ASC, id ASC',
    );
    return rows.map(ObligationModel.fromMap).toList();
  }

  Future<List<TransactionModel>> getTransactions() async {
    final db = await database;
    final rows = await db.query('transactions', orderBy: 'date_iso DESC, id DESC');
    return rows.map(TransactionModel.fromMap).toList();
  }

  Future<List<CategoryConfig>> getCategoryConfigs() async {
    final raw = await _getMetaValue('category_configs');
    if (raw == null || raw.isEmpty) {
      return defaultCategoryConfigs;
    }

    final decoded = (jsonDecode(raw) as List<dynamic>)
        .cast<Map<String, dynamic>>()
        .map((item) => CategoryConfig.fromJson(item))
        .toList();
    return decoded.isEmpty ? defaultCategoryConfigs : decoded;
  }

  Future<void> saveCategoryConfigs(List<CategoryConfig> categories) async {
    await _setMetaValue(
      key: 'category_configs',
      value: jsonEncode(categories.map((item) => item.toJson()).toList()),
    );
  }

  Future<List<TagConfig>> getTagConfigs() async {
    final raw = await _getMetaValue('tag_configs');
    if (raw == null || raw.isEmpty) {
      return defaultTagConfigs;
    }

    final decoded = (jsonDecode(raw) as List<dynamic>)
        .cast<Map<String, dynamic>>()
        .map((item) => TagConfig.fromJson(item))
        .toList();
    return decoded.isEmpty ? defaultTagConfigs : decoded;
  }

  Future<void> saveTagConfigs(List<TagConfig> tags) async {
    await _setMetaValue(
      key: 'tag_configs',
      value: jsonEncode(tags.map((item) => item.toJson()).toList()),
    );
  }

  Future<String> getSelectedPaletteId() async {
    return await _getMetaValue('theme_palette') ?? 'emerald_editorial';
  }

  Future<void> saveSelectedPaletteId(String paletteId) async {
    await _setMetaValue(key: 'theme_palette', value: paletteId);
  }

  Future<void> saveFixedIncome(FixedIncomeSourceModel source) async {
    final db = await database;

    if (source.id == null) {
      await db.insert('fixed_income_sources', source.toMap()..remove('id'));
      return;
    }

    await db.update(
      'fixed_income_sources',
      source.toMap()..remove('id'),
      where: 'id = ?',
      whereArgs: [source.id],
    );
  }

  Future<void> saveObligation(ObligationModel obligation) async {
    final db = await database;

    if (obligation.id == null) {
      await db.insert('obligations', obligation.toMap()..remove('id'));
      return;
    }

    await db.update(
      'obligations',
      obligation.toMap()..remove('id'),
      where: 'id = ?',
      whereArgs: [obligation.id],
    );
  }

  Future<void> insertTransaction(TransactionModel transaction) async {
    final db = await database;
    await db.insert('transactions', transaction.toMap()..remove('id'));
  }

  Future<bool> isSetupComplete() async {
    final raw = await _getMetaValue('setup_complete');
    return raw == 'true';
  }

  Future<void> setSetupComplete(bool value) async {
    await _setMetaValue(key: 'setup_complete', value: value ? 'true' : 'false');
  }

  Future<void> replaceFixedIncomeSources(List<FixedIncomeSourceModel> sources) async {
    final db = await database;
    await db.transaction((txn) async {
      await txn.delete('fixed_income_sources');
      for (final source in sources) {
        await txn.insert('fixed_income_sources', source.toMap()..remove('id'));
      }
    });
  }

  Future<void> replaceObligations(List<ObligationModel> obligations) async {
    final db = await database;
    await db.transaction((txn) async {
      await txn.delete('obligations');
      for (final obligation in obligations) {
        await txn.insert('obligations', obligation.toMap()..remove('id'));
      }
    });
  }

  Future<void> clearTransactions() async {
    final db = await database;
    await db.delete('transactions');
  }

  Future<void> resetFinancialSetup() async {
    final db = await database;
    await db.transaction((txn) async {
      await txn.delete('transactions');
      await txn.delete('obligations');
      await txn.delete('fixed_income_sources');
      await txn.insert(
        'app_meta',
        {
          'key': 'setup_complete',
          'value': 'false',
          'updated_at_iso': DateTime.now().toIso8601String(),
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    });
  }

  Future<String?> _getMetaValue(String key) async {
    final db = await database;
    final rows = await db.query(
      'app_meta',
      columns: ['value'],
      where: 'key = ?',
      whereArgs: [key],
      limit: 1,
    );
    if (rows.isEmpty) {
      return null;
    }

    return rows.first['value'] as String?;
  }

  Future<void> _setMetaValue({required String key, required String value}) async {
    final db = await database;
    await db.insert(
      'app_meta',
      {
        'key': key,
        'value': value,
        'updated_at_iso': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<Database> _open() async {
    final dbPath = _databasePathOverride ??
        path.join(await getDatabasesPath(), _databaseName);
    final options = OpenDatabaseOptions(
      version: currentVersion,
      onConfigure: (db) async {
        await db.execute('PRAGMA foreign_keys = ON');
      },
      onCreate: (db, version) async {
        await _createSchema(db);
        await _seedDatabase(db);
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        await _runMigrations(db, oldVersion, newVersion);
      },
    );

    final factory = _databaseFactory;
    if (factory != null) {
      return factory.openDatabase(dbPath, options: options);
    }

    return openDatabase(
      dbPath,
      version: currentVersion,
      onConfigure: options.onConfigure,
      onCreate: options.onCreate,
      onUpgrade: options.onUpgrade,
    );
  }

  Future<void> _createSchema(Database db) async {
    await _createFixedIncomeSourcesTable(db);
    await _createObligationsTable(db);
    await _createTransactionsTable(db);
    await _createAppMetaTable(db);
    await _createIndexes(db);
  }

  Future<void> _runMigrations(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2 && newVersion >= 2) {
      await _createAppMetaTable(db);
      await _createIndexes(db);
    }

    if (oldVersion < 3 && newVersion >= 3) {
      await db.execute(
        "ALTER TABLE fixed_income_sources ADD COLUMN cadence TEXT NOT NULL DEFAULT 'monthly'",
      );
      await db.execute(
        'ALTER TABLE fixed_income_sources ADD COLUMN expected_weekday INTEGER',
      );
    }

    if (oldVersion < 4 && newVersion >= 4) {
      await db.execute(
        "ALTER TABLE obligations ADD COLUMN cadence TEXT NOT NULL DEFAULT 'monthly'",
      );
      await db.execute(
        'ALTER TABLE obligations ADD COLUMN due_weekday INTEGER',
      );
    }

    if (oldVersion < 5 && newVersion >= 5) {
      await db.execute(
        'ALTER TABLE obligations ADD COLUMN category_id TEXT',
      );
    }
  }

  Future<void> _seedDatabase(Database db) async {
    final batch = db.batch();
    final now = DateTime.now();

    batch.insert('app_meta', {
      'key': 'category_configs',
      'value': jsonEncode(defaultCategoryConfigs.map((item) => item.toJson()).toList()),
      'updated_at_iso': now.toIso8601String(),
    });

    batch.insert('app_meta', {
      'key': 'tag_configs',
      'value': jsonEncode(defaultTagConfigs.map((item) => item.toJson()).toList()),
      'updated_at_iso': now.toIso8601String(),
    });

    batch.insert('app_meta', {
      'key': 'setup_complete',
      'value': 'false',
      'updated_at_iso': now.toIso8601String(),
    });

    batch.insert('app_meta', {
      'key': 'theme_palette',
      'value': 'emerald_editorial',
      'updated_at_iso': now.toIso8601String(),
    });

    await batch.commit(noResult: true);
  }

  Future<void> _createFixedIncomeSourcesTable(DatabaseExecutor db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS fixed_income_sources(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        amount REAL NOT NULL,
        cadence TEXT NOT NULL DEFAULT 'monthly',
        expected_day INTEGER NOT NULL,
        expected_weekday INTEGER,
        wallet TEXT NOT NULL,
        active INTEGER NOT NULL
      )
    ''');
  }

  Future<void> _createObligationsTable(DatabaseExecutor db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS obligations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        amount REAL NOT NULL,
        category_id TEXT,
        cadence TEXT NOT NULL DEFAULT 'monthly',
        due_day INTEGER NOT NULL,
        due_weekday INTEGER,
        kind TEXT NOT NULL,
        status TEXT NOT NULL
      )
    ''');
  }

  Future<void> _createTransactionsTable(DatabaseExecutor db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        amount REAL NOT NULL,
        wallet TEXT NOT NULL,
        category TEXT NOT NULL,
        tags TEXT NOT NULL,
        notes TEXT NOT NULL,
        date_iso TEXT NOT NULL,
        recurring INTEGER NOT NULL
      )
    ''');
  }

  Future<void> _createAppMetaTable(DatabaseExecutor db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS app_meta(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at_iso TEXT NOT NULL
      )
    ''');
  }

  Future<void> _createIndexes(DatabaseExecutor db) async {
    await db.execute(
      'CREATE INDEX IF NOT EXISTS idx_fixed_income_expected_day ON fixed_income_sources(expected_day)',
    );
    await db.execute(
      'CREATE INDEX IF NOT EXISTS idx_obligations_due_day ON obligations(due_day)',
    );
    await db.execute(
      'CREATE INDEX IF NOT EXISTS idx_transactions_date_iso ON transactions(date_iso DESC)',
    );
  }
}