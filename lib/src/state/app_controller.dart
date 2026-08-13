import 'package:flutter/foundation.dart';

import '../core/theme/app_theme.dart';
import '../data/app_database.dart';
import '../domain/allocation_engine.dart';
import '../domain/models.dart';

class AppController extends ChangeNotifier {
  AppController({required this.engine, this.database});

  factory AppController.preview() {
    final controller = AppController(engine: const IncomeAllocationEngine());
    controller._fixedIncomeSources = const [
      FixedIncomeSourceModel(
        id: 1,
        label: 'Salario principal',
        amount: 40000,
        cadence: FixedIncomeCadence.monthly,
        expectedDay: 30,
        wallet: 'Banco',
        active: true,
      ),
      FixedIncomeSourceModel(
        id: 2,
        label: 'Comision fija',
        amount: 16000,
        cadence: FixedIncomeCadence.biweekly,
        expectedDay: 15,
        wallet: 'Banco',
        active: true,
      ),
    ];
    controller._obligations = const [
      ObligationModel(
        id: 1,
        label: 'Casa',
        amount: 12000,
        categoryId: 'casa',
        cadence: FixedIncomeCadence.monthly,
        dueDay: 15,
        kind: 'Fija',
        status: 'Cubierto',
      ),
      ObligationModel(
        id: 2,
        label: 'Colegio',
        amount: 5600,
        categoryId: 'colegio',
        cadence: FixedIncomeCadence.monthly,
        dueDay: 20,
        kind: 'Fija',
        status: 'Pendiente',
      ),
      ObligationModel(
        id: 3,
        label: 'Manutencion',
        amount: 4200,
        categoryId: 'manutencion',
        cadence: FixedIncomeCadence.biweekly,
        dueDay: 15,
        kind: 'Fija',
        status: 'Pendiente',
      ),
    ];
    controller._transactions = [
      TransactionModel(
        id: 1,
        kind: TransactionKind.ingreso,
        amount: 30000,
        wallet: 'Banco',
        category: 'Nomina',
        tags: const ['Preview'],
        notes: '',
        date: DateTime.now(),
        recurring: false,
      ),
      TransactionModel(
        id: 2,
        kind: TransactionKind.gasto,
        amount: 4200,
        wallet: 'Banco',
        category: 'Casa',
        tags: const ['Preview'],
        notes: '',
        date: DateTime.now().subtract(const Duration(days: 3)),
        recurring: false,
      ),
      TransactionModel(
        id: 3,
        kind: TransactionKind.gasto,
        amount: 1800,
        wallet: 'Banco',
        category: 'Delivery',
        tags: const ['Preview'],
        notes: '',
        date: DateTime.now().subtract(const Duration(days: 2)),
        recurring: false,
      ),
      TransactionModel(
        id: 4,
        kind: TransactionKind.gasto,
        amount: 950,
        wallet: 'Efectivo',
        category: 'Transporte',
        tags: const ['Preview'],
        notes: '',
        date: DateTime(DateTime.now().year, DateTime.now().month - 1, 18),
        recurring: false,
      ),
    ];
    controller._categoryConfigs = defaultCategoryConfigs;
    controller._tagConfigs = defaultTagConfigs;
    controller._setupComplete = true;
    controller._selectedPaletteId = AppPalettes.emeraldEditorial.id;
    return controller;
  }

  final AppDatabase? database;
  final IncomeAllocationEngine engine;

  List<FixedIncomeSourceModel> _fixedIncomeSources = [];
  List<ObligationModel> _obligations = [];
  List<TransactionModel> _transactions = [];
  List<CategoryConfig> _categoryConfigs = [];
  List<TagConfig> _tagConfigs = [];
  bool _setupComplete = false;
  String _selectedPaletteId = AppPalettes.emeraldEditorial.id;

  List<FixedIncomeSourceModel> get fixedIncomeSources => List.unmodifiable(_fixedIncomeSources);
  List<ObligationModel> get obligations => List.unmodifiable(_obligations);
  List<TransactionModel> get transactions => List.unmodifiable(_transactions);
  List<CategoryConfig> get categoryConfigs => List.unmodifiable(_categoryConfigs);
  List<TagConfig> get tagConfigs => List.unmodifiable(_tagConfigs);
  List<CategoryConfig> get activeCategoryConfigs =>
      _categoryConfigs.where((item) => item.active).toList(growable: false);
    List<CategoryConfig> get activeExpenseCategoryConfigs => _categoryConfigs
      .where((item) => item.active && item.scope == CategoryScope.expense)
      .toList(growable: false);
    List<CategoryConfig> get activeIncomeCategoryConfigs => _categoryConfigs
      .where((item) => item.active && item.scope == CategoryScope.income)
      .toList(growable: false);
  List<TagConfig> get activeTagConfigs =>
      _tagConfigs.where((item) => item.active).toList(growable: false);
    bool get setupComplete => _setupComplete;
  String get selectedPaletteId => _selectedPaletteId;
  AppPaletteOption get selectedPalette => AppPalettes.byId(_selectedPaletteId);

  Future<void> load() async {
    if (database == null) {
      return;
    }

    _setupComplete = await database!.isSetupComplete();
    _categoryConfigs = await database!.getCategoryConfigs();
    _tagConfigs = await database!.getTagConfigs();
    _selectedPaletteId = await database!.getSelectedPaletteId();

    if (!_setupComplete && await database!.hasResidualFinancialData()) {
      await database!.resetFinancialSetup();
    }

    if (_setupComplete) {
      _fixedIncomeSources = await database!.getFixedIncomeSources();
      _obligations = await database!.getObligations();
      _transactions = await database!.getTransactions();
    } else {
      _fixedIncomeSources = [];
      _obligations = [];
      _transactions = [];
    }

    AppColors.usePalette(AppPalettes.byId(_selectedPaletteId));
    notifyListeners();
  }

  Future<void> saveFixedIncome(FixedIncomeSourceModel source) async {
    if (database == null) {
      final index = _fixedIncomeSources.indexWhere((item) => item.id == source.id);
      if (index == -1) {
        _fixedIncomeSources = [..._fixedIncomeSources, source.copyWith(id: _fixedIncomeSources.length + 1)];
      } else {
        _fixedIncomeSources[index] = source;
      }
      notifyListeners();
      return;
    }

    await database!.saveFixedIncome(source);
    await load();
  }

  Future<void> saveObligation(ObligationModel obligation) async {
    if (database == null) {
      final index = _obligations.indexWhere((item) => item.id == obligation.id);
      if (index == -1) {
        _obligations = [..._obligations, obligation.copyWith(id: _obligations.length + 1)];
      } else {
        _obligations[index] = obligation;
      }
      notifyListeners();
      return;
    }

    await database!.saveObligation(obligation);
    await load();
  }

  Future<void> addTransaction(TransactionModel transaction) async {
    if (database == null) {
      _transactions = [transaction.copyWith(id: _transactions.length + 1), ..._transactions];
      notifyListeners();
      return;
    }

    await database!.insertTransaction(transaction);
    await load();
  }

  Future<void> saveCategory(CategoryConfig category) async {
    final next = _upsertById(_categoryConfigs, category);

    if (database == null) {
      _categoryConfigs = next;
      notifyListeners();
      return;
    }

    await database!.saveCategoryConfigs(next);
    await load();
  }

  Future<void> saveTag(TagConfig tag) async {
    final next = _upsertById(_tagConfigs, tag);

    if (database == null) {
      _tagConfigs = next;
      notifyListeners();
      return;
    }

    await database!.saveTagConfigs(next);
    await load();
  }

  Future<void> completeInitialSetup({
    required List<FixedIncomeSourceModel> fixedIncomes,
    required List<ObligationModel> obligations,
  }) async {
    if (database == null) {
      _fixedIncomeSources = fixedIncomes;
      _obligations = obligations;
      _transactions = [];
      _setupComplete = true;
      notifyListeners();
      return;
    }

    await database!.replaceFixedIncomeSources(fixedIncomes);
    await database!.replaceObligations(obligations);
    await database!.clearTransactions();
    await database!.setSetupComplete(true);
    await load();
  }

  Future<void> resetInitialSetup() async {
    if (database == null) {
      _fixedIncomeSources = [];
      _obligations = [];
      _transactions = [];
      _setupComplete = false;
      notifyListeners();
      return;
    }

    await database!.resetFinancialSetup();
    await load();
  }

  Future<void> saveThemePalette(String paletteId) async {
    _selectedPaletteId = paletteId;
    AppColors.usePalette(AppPalettes.byId(paletteId));

    if (database == null) {
      notifyListeners();
      return;
    }

    await database!.saveSelectedPaletteId(paletteId);
    notifyListeners();
  }

  CategoryConfig? categoryForLabel(String label) {
    for (final category in _categoryConfigs) {
      if (category.label == label) {
        return category;
      }
    }

    return null;
  }

  CategoryConfig? categoryById(String? id) {
    if (id == null || id.isEmpty) {
      return null;
    }

    for (final category in _categoryConfigs) {
      if (category.id == id) {
        return category;
      }
    }

    return null;
  }

  double get fixedIncomeExpected {
    return _fixedIncomeSources
        .where((source) => source.active)
      .fold<double>(0, (sum, source) => sum + source.monthlyExpectedAmount);
  }

  double get incomeReportedThisMonth {
    final now = DateTime.now();
    return _transactions.where((transaction) {
      return transaction.kind.isIncome &&
          transaction.date.year == now.year &&
          transaction.date.month == now.month;
    }).fold<double>(0, (sum, transaction) => sum + transaction.amount);
  }

  double get pendingObligationsTotal {
    return _obligations
        .where((obligation) => obligation.status != 'Cubierto')
        .fold<double>(0, (sum, obligation) => sum + obligation.amount);
  }

  double get obligationsTarget {
    return _obligations.fold<double>(0, (sum, obligation) => sum + obligation.amount);
  }

  double get obligationsReserved {
    return _obligations
        .where((obligation) => obligation.status == 'Cubierto' || obligation.status == 'Parcial')
        .fold<double>(0, (sum, obligation) => sum + obligation.amount);
  }

  double get goalsTarget {
    return fixedIncomeExpected * 0.20;
  }

  double get goalsReserved {
    final savingsLike = _transactions.where(
      (transaction) => transaction.kind == TransactionKind.ahorro ||
          transaction.kind == TransactionKind.inversion ||
          transaction.kind == TransactionKind.deuda,
    );

    return savingsLike.fold<double>(0, (sum, transaction) => sum + transaction.amount);
  }

  double get personalSpentThisMonth {
    final now = DateTime.now();
    return _transactions.where((transaction) {
      return transaction.kind == TransactionKind.gasto &&
          transaction.date.year == now.year &&
          transaction.date.month == now.month;
    }).fold<double>(0, (sum, transaction) => sum + transaction.amount);
  }

  double get totalExpensesThisMonth {
    final now = DateTime.now();
    return _transactions.where((transaction) {
      return transaction.kind.affectsCashNegatively &&
          transaction.date.year == now.year &&
          transaction.date.month == now.month;
    }).fold<double>(0, (sum, transaction) => sum + transaction.amount);
  }

  double get safePersonalAvailable {
    return remainingPersonalRecommendedThisMonth;
  }

  double get latestIncomeAmount {
    for (final transaction in _transactions) {
      if (transaction.kind.isIncome) {
        return transaction.amount;
      }
    }

    return 0;
  }

  AllocationSuggestion get latestIncomeSuggestion => suggestionForAmount(latestIncomeAmount);

  double get recommendedPersonalBudgetThisMonth {
    return suggestionForAmount(incomeReportedThisMonth).forPersonal;
  }

  double get remainingPersonalRecommendedThisMonth {
    final remaining = recommendedPersonalBudgetThisMonth - personalSpentThisMonth;
    return remaining < 0 ? 0 : remaining;
  }

  double get incomeGap {
    final gap = fixedIncomeExpected - incomeReportedThisMonth;
    return gap > 0 ? gap : 0;
  }

  double get quincenaCoverage {
    if (obligationsTarget == 0) {
      return 1;
    }

    return (obligationsReserved / obligationsTarget).clamp(0, 1);
  }

  double get currentMonthExpenseTotal => _expenseTotalForMonth(DateTime.now());

  double get previousMonthExpenseTotal {
    final now = DateTime.now();
    return _expenseTotalForMonth(DateTime(now.year, now.month - 1, 1));
  }

  double get monthlyFixedOutflowTotal {
    return _obligations.fold<double>(0, (sum, obligation) => sum + obligation.amount);
  }

  double get reservePerQuincena => monthlyFixedOutflowTotal / 2;

  double get firstQuincenaReserveTarget {
    return _obligations
      .fold<double>(0, (sum, item) => sum + item.firstQuincenaAmount);
  }

  double get secondQuincenaReserveTarget {
    return _obligations
      .fold<double>(0, (sum, item) => sum + item.secondQuincenaAmount);
  }

  List<QuincenaReserveView> get quincenaReserveViews {
    return [
      QuincenaReserveView(
        label: 'Apartado por quincena',
        amount: reservePerQuincena,
        detail: 'Meta base si quieres repartir el mes en dos bloques iguales.',
      ),
      QuincenaReserveView(
        label: 'Primera quincena',
        amount: firstQuincenaReserveTarget,
        detail: 'Compromisos con vencimiento del dia 1 al 15.',
      ),
      QuincenaReserveView(
        label: 'Segunda quincena',
        amount: secondQuincenaReserveTarget,
        detail: 'Compromisos con vencimiento del dia 16 al cierre del mes.',
      ),
    ];
  }

  List<CategorySpendComparison> get expenseComparisons {
    final now = DateTime.now();
    final current = _expenseTotalsByCategory(now);
    final previous = _expenseTotalsByCategory(DateTime(now.year, now.month - 1, 1));
    final labels = {...current.keys, ...previous.keys}.toList()
      ..sort((left, right) => ((current[right] ?? 0) + (previous[right] ?? 0))
          .compareTo((current[left] ?? 0) + (previous[left] ?? 0)));

    return labels.take(5).map((label) {
      final category = categoryForLabel(label);
      return CategorySpendComparison(
        label: label,
        colorToken: category?.colorToken ?? 'gold',
        iconToken: category?.iconToken ?? 'receipt',
        currentAmount: current[label] ?? 0,
        previousAmount: previous[label] ?? 0,
      );
    }).toList(growable: false);
  }

  AllocationSuggestion suggestionForAmount(double amount) {
    return engine.suggest(
      amount: amount,
      snapshot: FinancialSnapshot(
        fixedIncomeExpected: fixedIncomeExpected,
        incomeReported: incomeReportedThisMonth,
        pendingObligations: pendingObligationsTotal,
      ),
    );
  }

  bool expenseBreaksReserve(double amount) {
    return amount > safePersonalAvailable;
  }

  List<WalletBalanceView> get walletBalances {
    return walletOptions.map((wallet) {
      double amount = 0;

      for (final transaction in _transactions) {
        if (transaction.wallet != wallet) {
          continue;
        }

        if (transaction.kind.isIncome) {
          amount += transaction.amount;
        } else if (transaction.kind.affectsCashNegatively) {
          amount -= transaction.amount;
        }
      }

      return WalletBalanceView(label: wallet, amount: amount);
    }).toList();
  }

  List<BucketOverview> get bucketOverviews {
    final personalTarget = fixedIncomeExpected * 0.30;
    final personalUsed = totalExpensesThisMonth - goalsReserved;

    return [
      BucketOverview(
        label: 'Obligaciones fijas',
        reserved: obligationsReserved,
        total: obligationsTarget,
      ),
      BucketOverview(
        label: 'Personal',
        reserved: personalUsed < 0 ? 0 : personalUsed,
        total: personalTarget,
      ),
      BucketOverview(
        label: 'Ahorro, inversion y deuda',
        reserved: goalsReserved,
        total: goalsTarget,
      ),
    ];
  }

  List<InsightView> get generatedInsights {
    final deliveryExpenses = _transactions
        .where((transaction) => transaction.category == 'Delivery')
        .fold<double>(0, (sum, transaction) => sum + transaction.amount);
    final insights = <InsightView>[];

    if (deliveryExpenses > 2500) {
      insights.add(
        const InsightView(
          title: 'Delivery por encima de tendencia',
          body: 'Tus gastos en delivery ya superan el umbral mensual esperado. Conviene recortar antes de abrir mas presupuesto personal.',
        ),
      );
    }

    if (incomeReportedThisMonth >= fixedIncomeExpected) {
      insights.add(
        const InsightView(
          title: 'Capacidad de ahorro al alza',
          body: 'Ya alcanzaste o superaste el minimo esperado del mes; puedes desviar una mayor parte del siguiente ingreso a ahorro o inversion.',
        ),
      );
    } else {
      insights.add(
        InsightView(
          title: 'Ingreso base aun incompleto',
          body: 'Todavia faltan ${incomeGap.toStringAsFixed(0)} para llegar al ingreso fijo esperado. El motor debe ser conservador con gasto personal.',
        ),
      );
    }

    insights.add(
      InsightView(
        title: 'Disponible personal real',
        body: 'Con los ingresos ya registrados, te quedan ${remainingPersonalRecommendedThisMonth.toStringAsFixed(0)} dentro de la recomendacion personal del mes.',
      ),
    );

    return insights;
  }

  List<T> _upsertById<T>(List<T> current, T item) {
    final next = [...current];
    final id = switch (item) {
      CategoryConfig config => config.id,
      TagConfig tag => tag.id,
      _ => '',
    };

    final index = next.indexWhere((entry) {
      return switch (entry) {
        CategoryConfig config => config.id == id,
        TagConfig tag => tag.id == id,
        _ => false,
      };
    });

    if (index == -1) {
      next.add(item);
    } else {
      next[index] = item;
    }

    return next;
  }

  double _expenseTotalForMonth(DateTime month) {
    return _transactions.where((transaction) {
      return transaction.kind == TransactionKind.gasto &&
          transaction.date.year == month.year &&
          transaction.date.month == month.month;
    }).fold<double>(0, (sum, transaction) => sum + transaction.amount);
  }

  Map<String, double> _expenseTotalsByCategory(DateTime month) {
    final totals = <String, double>{};

    for (final transaction in _transactions) {
      if (transaction.kind != TransactionKind.gasto ||
          transaction.date.year != month.year ||
          transaction.date.month != month.month) {
        continue;
      }

      totals.update(
        transaction.category,
        (value) => value + transaction.amount,
        ifAbsent: () => transaction.amount,
      );
    }

    return totals;
  }
}

extension on TransactionModel {
  TransactionModel copyWith({int? id}) {
    return TransactionModel(
      id: id ?? this.id,
      kind: kind,
      amount: amount,
      wallet: wallet,
      category: category,
      tags: tags,
      notes: notes,
      date: date,
      recurring: recurring,
    );
  }
}