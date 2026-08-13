import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as path;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:prep_personal/src/data/app_database.dart';
import 'package:prep_personal/src/domain/allocation_engine.dart';
import 'package:prep_personal/src/domain/models.dart';
import 'package:prep_personal/src/state/app_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempDirectory;

  setUpAll(() {
    sqfliteFfiInit();
  });

  setUp(() async {
    tempDirectory = await Directory.systemTemp.createTemp('prep_personal_controller_test_');
  });

  tearDown(() async {
    if (tempDirectory.existsSync()) {
      await tempDirectory.delete(recursive: true);
    }
  });

  test('load clears residual financial data while setup is incomplete', () async {
    final database = AppDatabase(
      databaseFactoryOverride: databaseFactoryFfi,
      databasePathOverride: path.join(tempDirectory.path, 'prep_personal_controller.db'),
    );
    addTearDown(database.close);

    await database.initialize();
    await database.saveFixedIncome(
      const FixedIncomeSourceModel(
        label: 'Pago semanal',
        amount: 2500,
        cadence: FixedIncomeCadence.weekly,
        expectedDay: 1,
        expectedWeekday: DateTime.monday,
        wallet: 'Banco',
        active: true,
      ),
    );
    await database.insertTransaction(
      TransactionModel(
        kind: TransactionKind.ingreso,
        amount: 2500,
        wallet: 'Banco',
        category: 'Pago semanal',
        tags: const ['Residuo'],
        notes: '',
        date: DateTime(2099, 1, 5),
        recurring: false,
      ),
    );

    final controller = AppController(
      engine: const IncomeAllocationEngine(),
      database: database,
    );

    await controller.load();

    expect(controller.setupComplete, isFalse);
    expect(controller.fixedIncomeSources, isEmpty);
    expect(controller.transactions, isEmpty);
    expect(await database.hasResidualFinancialData(), isFalse);
  });

  test('tracks latest income suggestion separately from monthly remaining personal budget', () async {
    final database = AppDatabase(
      databaseFactoryOverride: databaseFactoryFfi,
      databasePathOverride: path.join(tempDirectory.path, 'prep_personal_controller_metrics.db'),
    );
    addTearDown(database.close);

    await database.initialize();
    await database.setSetupComplete(true);

    await database.saveFixedIncome(
      const FixedIncomeSourceModel(
        label: 'Nomina base',
        amount: 422750,
        cadence: FixedIncomeCadence.monthly,
        expectedDay: 30,
        wallet: 'Banco',
        active: true,
      ),
    );

    await database.saveObligation(
      const ObligationModel(
        label: 'Disney plus',
        amount: 649,
        categoryId: 'netflix',
        cadence: FixedIncomeCadence.monthly,
        dueDay: 30,
        kind: 'Fija',
        status: 'Pendiente',
      ),
    );

    await database.insertTransaction(
      TransactionModel(
        kind: TransactionKind.ingreso,
        amount: 74500,
        wallet: 'Banco',
        category: 'Nomina',
        tags: const [],
        notes: '',
        date: DateTime.now().subtract(const Duration(days: 1)),
        recurring: false,
      ),
    );

    await database.insertTransaction(
      TransactionModel(
        kind: TransactionKind.ingreso,
        amount: 85375,
        wallet: 'Banco',
        category: 'Trabajo',
        tags: const [],
        notes: '',
        date: DateTime.now(),
        recurring: false,
      ),
    );

    final controller = AppController(
      engine: const IncomeAllocationEngine(),
      database: database,
    );

    await controller.load();

    expect(controller.latestIncomeAmount, 85375);
    expect(controller.latestIncomeSuggestion.forPersonal, 15367.5);
    expect(controller.recommendedPersonalBudgetThisMonth, 28777.5);
    expect(controller.remainingPersonalRecommendedThisMonth, 28777.5);
  });
}