import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as path;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:prep_personal/src/data/app_database.dart';
import 'package:prep_personal/src/domain/models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempDirectory;

  setUpAll(() {
    sqfliteFfiInit();
  });

  setUp(() async {
    tempDirectory = await Directory.systemTemp.createTemp('prep_personal_db_test_');
  });

  tearDown(() async {
    if (tempDirectory.existsSync()) {
      await tempDirectory.delete(recursive: true);
    }
  });

  test('persists and updates fixed incomes plus new transactions', () async {
    final database = AppDatabase(
      databaseFactoryOverride: databaseFactoryFfi,
      databasePathOverride: path.join(tempDirectory.path, 'prep_personal_test.db'),
    );
    addTearDown(database.close);

    await database.initialize();

    final initialSources = await database.getFixedIncomeSources();
    expect(initialSources, isEmpty);
    expect(await database.isSetupComplete(), isFalse);

    await database.saveFixedIncome(
      const FixedIncomeSourceModel(
        label: 'Freelance fijo',
        amount: 5500,
        cadence: FixedIncomeCadence.monthly,
        expectedDay: 12,
        wallet: 'Banco',
        active: true,
      ),
    );

    final sourcesAfterInsert = await database.getFixedIncomeSources();
    final insertedSource = sourcesAfterInsert.firstWhere((item) => item.label == 'Freelance fijo');
    expect(insertedSource.amount, 5500);
    expect(insertedSource.active, isTrue);

    await database.saveFixedIncome(
      insertedSource.copyWith(amount: 6200, active: false),
    );

    final sourcesAfterUpdate = await database.getFixedIncomeSources();
    final updatedSource = sourcesAfterUpdate.firstWhere((item) => item.id == insertedSource.id);
    expect(updatedSource.amount, 6200);
    expect(updatedSource.active, isFalse);
    expect(updatedSource.cadence, FixedIncomeCadence.monthly);

    await database.saveObligation(
      const ObligationModel(
        label: 'Prestamo personal',
        amount: 9000,
        categoryId: 'deuda',
        cadence: FixedIncomeCadence.biweekly,
        dueDay: 15,
        kind: 'Fija',
        status: 'Pendiente',
      ),
    );

    final obligationsAfterInsert = await database.getObligations();
    final insertedObligation = obligationsAfterInsert.firstWhere((item) => item.label == 'Prestamo personal');
    expect(insertedObligation.amount, 9000);
    expect(insertedObligation.cadence, FixedIncomeCadence.biweekly);
    expect(insertedObligation.categoryId, 'deuda');

    await database.saveObligation(
      insertedObligation.copyWith(
        cadence: FixedIncomeCadence.weekly,
        dueWeekday: DateTime.friday,
      ),
    );

    final obligationsAfterUpdate = await database.getObligations();
    final updatedObligation = obligationsAfterUpdate.firstWhere((item) => item.id == insertedObligation.id);
    expect(updatedObligation.cadence, FixedIncomeCadence.weekly);
    expect(updatedObligation.dueWeekday, DateTime.friday);

    final categories = await database.getCategoryConfigs();
    await database.saveCategoryConfigs([
      ...categories,
      const CategoryConfig(
        id: 'mascotas',
        label: 'Mascotas',
        scope: CategoryScope.expense,
        type: 'Variable',
        colorToken: 'plum',
        iconToken: 'favorite',
      ),
    ]);
    final tags = await database.getTagConfigs();
    await database.saveTagConfigs([
      ...tags,
      const TagConfig(
        id: 'veterinaria',
        label: 'Veterinaria',
        colorToken: 'sage',
      ),
    ]);

    final savedCategories = await database.getCategoryConfigs();
    final savedTags = await database.getTagConfigs();
    expect(savedCategories.any((item) => item.label == 'Mascotas'), isTrue);
    expect(savedTags.any((item) => item.label == 'Veterinaria'), isTrue);

    await database.insertTransaction(
      TransactionModel(
        kind: TransactionKind.ingreso,
        amount: 9100,
        wallet: 'Banco',
        category: 'Ingreso extra',
        tags: const ['Test'],
        notes: 'Ingreso de prueba',
        date: DateTime(2099, 1, 1, 10, 30),
        recurring: false,
      ),
    );

    final transactions = await database.getTransactions();
    expect(transactions.first.category, 'Ingreso extra');
    expect(transactions.first.tags, ['Test']);

    await database.setSetupComplete(true);
    expect(await database.isSetupComplete(), isTrue);

    await database.saveSelectedPaletteId('ocean_ledger');
    expect(await database.getSelectedPaletteId(), 'ocean_ledger');
  });

  test('migrates a version 1 database without losing existing rows', () async {
    final dbPath = path.join(tempDirectory.path, 'prep_personal_v1.db');

    final legacyDatabase = await databaseFactoryFfi.openDatabase(
      dbPath,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, version) async {
          await db.execute('''
            CREATE TABLE fixed_income_sources(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              label TEXT NOT NULL,
              amount REAL NOT NULL,
              expected_day INTEGER NOT NULL,
              wallet TEXT NOT NULL,
              active INTEGER NOT NULL
            )
          ''');

          await db.execute('''
            CREATE TABLE obligations(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              label TEXT NOT NULL,
              amount REAL NOT NULL,
              due_day INTEGER NOT NULL,
              kind TEXT NOT NULL,
              status TEXT NOT NULL
            )
          ''');

          await db.execute('''
            CREATE TABLE transactions(
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

          await db.insert('fixed_income_sources', {
            'label': 'Legacy salary',
            'amount': 30000,
            'expected_day': 30,
            'wallet': 'Banco',
            'active': 1,
          });
        },
      ),
    );
    await legacyDatabase.close();

    final database = AppDatabase(
      databaseFactoryOverride: databaseFactoryFfi,
      databasePathOverride: dbPath,
    );
    addTearDown(database.close);

    await database.initialize();

    final migratedRows = await database.getFixedIncomeSources();
    expect(migratedRows.any((item) => item.label == 'Legacy salary'), isTrue);
    expect(migratedRows.first.cadence, FixedIncomeCadence.monthly);

    final openedObligations = await database.getObligations();
    expect(openedObligations, isEmpty);

    final openedDatabase = await database.database;
    final metaTable = await openedDatabase.query(
      'sqlite_master',
      columns: ['name'],
      where: 'type = ? AND name = ?',
      whereArgs: ['table', 'app_meta'],
    );
    expect(metaTable, isNotEmpty);
    expect(await openedDatabase.getVersion(), AppDatabase.currentVersion);
  });

  test('reset clears residual financial data', () async {
    final database = AppDatabase(
      databaseFactoryOverride: databaseFactoryFfi,
      databasePathOverride: path.join(tempDirectory.path, 'prep_personal_reset.db'),
    );
    addTearDown(database.close);

    await database.initialize();
    await database.saveFixedIncome(
      const FixedIncomeSourceModel(
        label: 'Semanal',
        amount: 2000,
        cadence: FixedIncomeCadence.weekly,
        expectedDay: 1,
        expectedWeekday: DateTime.friday,
        wallet: 'Banco',
        active: true,
      ),
    );
    await database.insertTransaction(
      TransactionModel(
        kind: TransactionKind.ingreso,
        amount: 2000,
        wallet: 'Banco',
        category: 'Semanal',
        tags: const [],
        notes: '',
        date: DateTime(2099, 1, 2),
        recurring: false,
      ),
    );

    expect(await database.hasResidualFinancialData(), isTrue);

    await database.resetFinancialSetup();

    expect(await database.getFixedIncomeSources(), isEmpty);
    expect(await database.getTransactions(), isEmpty);
    expect(await database.isSetupComplete(), isFalse);
  });
}