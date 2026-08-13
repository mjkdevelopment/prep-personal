enum TransactionKind { ingreso, gasto, transferencia, ahorro, inversion, deuda }

enum FixedIncomeCadence { monthly, biweekly, weekly }

enum CategoryScope { expense, income }

extension CategoryScopeX on CategoryScope {
  String get dbValue => switch (this) {
        CategoryScope.expense => 'expense',
        CategoryScope.income => 'income',
      };

  String get label => switch (this) {
        CategoryScope.expense => 'Gasto',
        CategoryScope.income => 'Ingreso',
      };

  static CategoryScope fromDb(String? value) {
    return CategoryScope.values.firstWhere(
      (item) => item.dbValue == value,
      orElse: () => CategoryScope.expense,
    );
  }
}

extension FixedIncomeCadenceX on FixedIncomeCadence {
  String get dbValue => switch (this) {
        FixedIncomeCadence.monthly => 'monthly',
        FixedIncomeCadence.biweekly => 'biweekly',
        FixedIncomeCadence.weekly => 'weekly',
      };

  String get label => switch (this) {
        FixedIncomeCadence.monthly => 'Mensual',
        FixedIncomeCadence.biweekly => 'Quincenal',
        FixedIncomeCadence.weekly => 'Semanal',
      };

  static FixedIncomeCadence fromDb(String? value) {
    return FixedIncomeCadence.values.firstWhere(
      (item) => item.dbValue == value,
      orElse: () => FixedIncomeCadence.monthly,
    );
  }
}

extension WeekdayLabelX on int {
  String get weekdayLabel => switch (this) {
        DateTime.monday => 'Lunes',
        DateTime.tuesday => 'Martes',
        DateTime.wednesday => 'Miercoles',
        DateTime.thursday => 'Jueves',
        DateTime.friday => 'Viernes',
        DateTime.saturday => 'Sabado',
        DateTime.sunday => 'Domingo',
        _ => 'Lunes',
      };
}

extension TransactionKindX on TransactionKind {
  String get dbValue => switch (this) {
        TransactionKind.ingreso => 'ingreso',
        TransactionKind.gasto => 'gasto',
        TransactionKind.transferencia => 'transferencia',
        TransactionKind.ahorro => 'ahorro',
        TransactionKind.inversion => 'inversion',
        TransactionKind.deuda => 'deuda',
      };

  String get label => switch (this) {
        TransactionKind.ingreso => 'Ingreso',
        TransactionKind.gasto => 'Gasto',
        TransactionKind.transferencia => 'Transferencia',
        TransactionKind.ahorro => 'Ahorro',
        TransactionKind.inversion => 'Inversion',
        TransactionKind.deuda => 'Deuda',
      };

  bool get isIncome => this == TransactionKind.ingreso;

  bool get affectsCashNegatively => switch (this) {
        TransactionKind.gasto ||
        TransactionKind.ahorro ||
        TransactionKind.inversion ||
        TransactionKind.deuda => true,
        TransactionKind.ingreso || TransactionKind.transferencia => false,
      };

  static TransactionKind fromDb(String value) {
    return TransactionKind.values.firstWhere(
      (kind) => kind.dbValue == value,
      orElse: () => TransactionKind.gasto,
    );
  }

  static TransactionKind fromLabel(String value) {
    return TransactionKind.values.firstWhere(
      (kind) => kind.label == value,
      orElse: () => TransactionKind.ingreso,
    );
  }
}

class FixedIncomeSourceModel {
  const FixedIncomeSourceModel({
    this.id,
    required this.label,
    required this.amount,
    required this.cadence,
    required this.expectedDay,
    this.expectedWeekday,
    required this.wallet,
    required this.active,
  });

  final int? id;
  final String label;
  final double amount;
  final FixedIncomeCadence cadence;
  final int expectedDay;
  final int? expectedWeekday;
  final String wallet;
  final bool active;

  double get monthlyExpectedAmount => amount;

  double get installmentExpectedAmount => switch (cadence) {
        FixedIncomeCadence.monthly => amount,
        FixedIncomeCadence.biweekly => amount / 2,
        FixedIncomeCadence.weekly => amount / 4,
      };

  String get scheduleLabel => switch (cadence) {
        FixedIncomeCadence.monthly => 'Mensual · Dia $expectedDay',
        FixedIncomeCadence.biweekly => 'Quincenal · Dias 15 y 30',
        FixedIncomeCadence.weekly => 'Semanal · ${((expectedWeekday ?? DateTime.monday)).weekdayLabel}',
      };

  FixedIncomeSourceModel copyWith({
    int? id,
    String? label,
    double? amount,
    FixedIncomeCadence? cadence,
    int? expectedDay,
    int? expectedWeekday,
    String? wallet,
    bool? active,
  }) {
    return FixedIncomeSourceModel(
      id: id ?? this.id,
      label: label ?? this.label,
      amount: amount ?? this.amount,
      cadence: cadence ?? this.cadence,
      expectedDay: expectedDay ?? this.expectedDay,
      expectedWeekday: expectedWeekday ?? this.expectedWeekday,
      wallet: wallet ?? this.wallet,
      active: active ?? this.active,
    );
  }

  Map<String, Object?> toMap() {
    return {
      'id': id,
      'label': label,
      'amount': amount,
      'cadence': cadence.dbValue,
      'expected_day': expectedDay,
      'expected_weekday': expectedWeekday,
      'wallet': wallet,
      'active': active ? 1 : 0,
    };
  }

  factory FixedIncomeSourceModel.fromMap(Map<String, Object?> map) {
    return FixedIncomeSourceModel(
      id: map['id'] as int?,
      label: map['label'] as String,
      amount: (map['amount'] as num).toDouble(),
      cadence: FixedIncomeCadenceX.fromDb(map['cadence'] as String?),
      expectedDay: map['expected_day'] as int,
      expectedWeekday: map['expected_weekday'] as int?,
      wallet: map['wallet'] as String,
      active: (map['active'] as int) == 1,
    );
  }
}

class ObligationModel {
  const ObligationModel({
    this.id,
    required this.label,
    required this.amount,
    this.categoryId,
    required this.cadence,
    required this.dueDay,
    this.dueWeekday,
    required this.kind,
    required this.status,
  });

  final int? id;
  final String label;
  final double amount;
  final String? categoryId;
  final FixedIncomeCadence cadence;
  final int dueDay;
  final int? dueWeekday;
  final String kind;
  final String status;

  double get monthlyExpectedAmount => amount;

  double get installmentExpectedAmount => switch (cadence) {
        FixedIncomeCadence.monthly => amount,
        FixedIncomeCadence.biweekly => amount / 2,
        FixedIncomeCadence.weekly => amount / 4,
      };

  String get scheduleLabel => switch (cadence) {
        FixedIncomeCadence.monthly => 'Mensual · Dia $dueDay',
        FixedIncomeCadence.biweekly => 'Quincenal · Dias 15 y 30',
        FixedIncomeCadence.weekly => 'Semanal · ${((dueWeekday ?? DateTime.monday)).weekdayLabel}',
      };

  double get firstQuincenaAmount => switch (cadence) {
        FixedIncomeCadence.monthly => dueDay <= 15 ? amount : 0,
        FixedIncomeCadence.biweekly => amount / 2,
        FixedIncomeCadence.weekly => amount / 2,
      };

  double get secondQuincenaAmount => switch (cadence) {
        FixedIncomeCadence.monthly => dueDay > 15 ? amount : 0,
        FixedIncomeCadence.biweekly => amount / 2,
        FixedIncomeCadence.weekly => amount / 2,
      };

  ObligationModel copyWith({
    int? id,
    String? label,
    double? amount,
    String? categoryId,
    FixedIncomeCadence? cadence,
    int? dueDay,
    int? dueWeekday,
    String? kind,
    String? status,
  }) {
    return ObligationModel(
      id: id ?? this.id,
      label: label ?? this.label,
      amount: amount ?? this.amount,
      categoryId: categoryId ?? this.categoryId,
      cadence: cadence ?? this.cadence,
      dueDay: dueDay ?? this.dueDay,
      dueWeekday: dueWeekday ?? this.dueWeekday,
      kind: kind ?? this.kind,
      status: status ?? this.status,
    );
  }

  Map<String, Object?> toMap() {
    return {
      'id': id,
      'label': label,
      'amount': amount,
      'category_id': categoryId,
      'cadence': cadence.dbValue,
      'due_day': dueDay,
      'due_weekday': dueWeekday,
      'kind': kind,
      'status': status,
    };
  }

  factory ObligationModel.fromMap(Map<String, Object?> map) {
    return ObligationModel(
      id: map['id'] as int?,
      label: map['label'] as String,
      amount: (map['amount'] as num).toDouble(),
      categoryId: map['category_id'] as String?,
      cadence: FixedIncomeCadenceX.fromDb(map['cadence'] as String?),
      dueDay: map['due_day'] as int,
      dueWeekday: map['due_weekday'] as int?,
      kind: map['kind'] as String,
      status: map['status'] as String,
    );
  }
}

class TransactionModel {
  const TransactionModel({
    this.id,
    required this.kind,
    required this.amount,
    required this.wallet,
    required this.category,
    required this.tags,
    required this.notes,
    required this.date,
    required this.recurring,
  });

  final int? id;
  final TransactionKind kind;
  final double amount;
  final String wallet;
  final String category;
  final List<String> tags;
  final String notes;
  final DateTime date;
  final bool recurring;

  Map<String, Object?> toMap() {
    return {
      'id': id,
      'kind': kind.dbValue,
      'amount': amount,
      'wallet': wallet,
      'category': category,
      'tags': tags.join('|'),
      'notes': notes,
      'date_iso': date.toIso8601String(),
      'recurring': recurring ? 1 : 0,
    };
  }

  factory TransactionModel.fromMap(Map<String, Object?> map) {
    final rawTags = (map['tags'] as String?) ?? '';

    return TransactionModel(
      id: map['id'] as int?,
      kind: TransactionKindX.fromDb(map['kind'] as String),
      amount: (map['amount'] as num).toDouble(),
      wallet: map['wallet'] as String,
      category: map['category'] as String,
      tags: rawTags.isEmpty ? const [] : rawTags.split('|'),
      notes: (map['notes'] as String?) ?? '',
      date: DateTime.parse(map['date_iso'] as String),
      recurring: (map['recurring'] as int) == 1,
    );
  }
}

class AllocationSuggestion {
  const AllocationSuggestion({
    required this.forObligations,
    required this.forGoals,
    required this.forPersonal,
    required this.rationale,
  });

  final double forObligations;
  final double forGoals;
  final double forPersonal;
  final String rationale;
}

class FinancialSnapshot {
  const FinancialSnapshot({
    required this.fixedIncomeExpected,
    required this.incomeReported,
    required this.pendingObligations,
  });

  final double fixedIncomeExpected;
  final double incomeReported;
  final double pendingObligations;
}

class WalletBalanceView {
  const WalletBalanceView({required this.label, required this.amount});

  final String label;
  final double amount;
}

class BucketOverview {
  const BucketOverview({
    required this.label,
    required this.reserved,
    required this.total,
  });

  final String label;
  final double reserved;
  final double total;
}

class InsightView {
  const InsightView({required this.title, required this.body});

  final String title;
  final String body;
}

class CategoryConfig {
  const CategoryConfig({
    required this.id,
    required this.label,
    required this.scope,
    required this.type,
    required this.colorToken,
    required this.iconToken,
    this.active = true,
  });

  final String id;
  final String label;
  final CategoryScope scope;
  final String type;
  final String colorToken;
  final String iconToken;
  final bool active;

  CategoryConfig copyWith({
    String? id,
    String? label,
    CategoryScope? scope,
    String? type,
    String? colorToken,
    String? iconToken,
    bool? active,
  }) {
    return CategoryConfig(
      id: id ?? this.id,
      label: label ?? this.label,
      scope: scope ?? this.scope,
      type: type ?? this.type,
      colorToken: colorToken ?? this.colorToken,
      iconToken: iconToken ?? this.iconToken,
      active: active ?? this.active,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'label': label,
      'scope': scope.dbValue,
      'type': type,
      'colorToken': colorToken,
      'iconToken': iconToken,
      'active': active,
    };
  }

  factory CategoryConfig.fromJson(Map<String, Object?> json) {
    return CategoryConfig(
      id: json['id'] as String,
      label: json['label'] as String,
      scope: CategoryScopeX.fromDb(json['scope'] as String?),
      type: json['type'] as String,
      colorToken: json['colorToken'] as String,
      iconToken: json['iconToken'] as String,
      active: (json['active'] as bool?) ?? true,
    );
  }
}

class TagConfig {
  const TagConfig({
    required this.id,
    required this.label,
    required this.colorToken,
    this.active = true,
  });

  final String id;
  final String label;
  final String colorToken;
  final bool active;

  TagConfig copyWith({
    String? id,
    String? label,
    String? colorToken,
    bool? active,
  }) {
    return TagConfig(
      id: id ?? this.id,
      label: label ?? this.label,
      colorToken: colorToken ?? this.colorToken,
      active: active ?? this.active,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'label': label,
      'colorToken': colorToken,
      'active': active,
    };
  }

  factory TagConfig.fromJson(Map<String, Object?> json) {
    return TagConfig(
      id: json['id'] as String,
      label: json['label'] as String,
      colorToken: json['colorToken'] as String,
      active: (json['active'] as bool?) ?? true,
    );
  }
}

class CategorySpendComparison {
  const CategorySpendComparison({
    required this.label,
    required this.colorToken,
    required this.iconToken,
    required this.currentAmount,
    required this.previousAmount,
  });

  final String label;
  final String colorToken;
  final String iconToken;
  final double currentAmount;
  final double previousAmount;
}

class QuincenaReserveView {
  const QuincenaReserveView({
    required this.label,
    required this.amount,
    required this.detail,
  });

  final String label;
  final double amount;
  final String detail;
}

const defaultCategoryConfigs = [
  CategoryConfig(id: 'nomina', label: 'Nomina', scope: CategoryScope.income, type: 'Nomina', colorToken: 'emerald', iconToken: 'work'),
  CategoryConfig(id: 'trabajo', label: 'Trabajo', scope: CategoryScope.income, type: 'Trabajo', colorToken: 'petrol', iconToken: 'briefcase'),
  CategoryConfig(id: 'regalo', label: 'Regalo', scope: CategoryScope.income, type: 'Regalo', colorToken: 'coral', iconToken: 'redeem'),
  CategoryConfig(id: 'intereses', label: 'Intereses', scope: CategoryScope.income, type: 'Intereses', colorToken: 'gold', iconToken: 'account_balance'),
  CategoryConfig(id: 'comision', label: 'Comision', scope: CategoryScope.income, type: 'Comision', colorToken: 'sky', iconToken: 'paid'),
  CategoryConfig(id: 'renta', label: 'Renta', scope: CategoryScope.income, type: 'Renta', colorToken: 'plum', iconToken: 'apartment'),
  CategoryConfig(id: 'casa', label: 'Casa', scope: CategoryScope.expense, type: 'Fija', colorToken: 'amber', iconToken: 'home'),
  CategoryConfig(id: 'luz', label: 'Luz', scope: CategoryScope.expense, type: 'Fija', colorToken: 'gold', iconToken: 'bolt'),
  CategoryConfig(id: 'agua', label: 'Agua', scope: CategoryScope.expense, type: 'Fija', colorToken: 'sky', iconToken: 'water'),
  CategoryConfig(id: 'netflix', label: 'Netflix', scope: CategoryScope.expense, type: 'Fija', colorToken: 'coral', iconToken: 'tv'),
  CategoryConfig(id: 'colegio', label: 'Colegio', scope: CategoryScope.expense, type: 'Fija', colorToken: 'sage', iconToken: 'school'),
  CategoryConfig(id: 'delivery', label: 'Delivery', scope: CategoryScope.expense, type: 'Variable', colorToken: 'coral', iconToken: 'restaurant'),
  CategoryConfig(id: 'transporte', label: 'Transporte', scope: CategoryScope.expense, type: 'Variable', colorToken: 'petrol', iconToken: 'commute'),
  CategoryConfig(id: 'nomina-mama', label: 'Nomina Mama', scope: CategoryScope.expense, type: 'Nomina', colorToken: 'plum', iconToken: 'group'),
  CategoryConfig(id: 'manutencion', label: 'Manutencion', scope: CategoryScope.expense, type: 'Fija', colorToken: 'sage', iconToken: 'favorite'),
  CategoryConfig(id: 'ahorro', label: 'Ahorro', scope: CategoryScope.expense, type: 'Meta', colorToken: 'emerald', iconToken: 'savings'),
  CategoryConfig(id: 'inversion', label: 'Inversion', scope: CategoryScope.expense, type: 'Meta', colorToken: 'sky', iconToken: 'trending'),
  CategoryConfig(id: 'deuda', label: 'Deuda', scope: CategoryScope.expense, type: 'Meta', colorToken: 'terracotta', iconToken: 'receipt'),
];

const defaultTagConfigs = [
  TagConfig(id: 'pedidosya', label: 'PedidosYa', colorToken: 'coral'),
  TagConfig(id: 'callejera', label: 'Callejera', colorToken: 'amber'),
  TagConfig(id: 'oficina', label: 'Oficina', colorToken: 'sky'),
  TagConfig(id: 'nino', label: 'Nino', colorToken: 'plum'),
  TagConfig(id: 'salud', label: 'Salud', colorToken: 'sage'),
  TagConfig(id: 'streaming', label: 'Streaming', colorToken: 'gold'),
];

final categoryOptions = [
  for (final category in defaultCategoryConfigs.where((item) => item.scope == CategoryScope.expense)) category.label,
];

final quickTagOptions = [
  for (final tag in defaultTagConfigs) tag.label,
];

const walletOptions = ['Efectivo', 'Banco', 'Cooperativa'];

const categoryTypeLabels = {
  'Casa': 'Fija',
  'Luz': 'Fija',
  'Agua': 'Fija',
  'Netflix': 'Fija',
  'Colegio': 'Fija',
  'Delivery': 'Variable',
  'Transporte': 'Variable',
  'Nomina Mama': 'Nomina',
  'Manutencion': 'Fija',
  'Ahorro': 'Meta',
  'Inversion': 'Meta',
  'Deuda': 'Meta',
};