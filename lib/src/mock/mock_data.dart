class BucketSummary {
  const BucketSummary({
    required this.label,
    required this.reserved,
    required this.total,
  });

  final String label;
  final double reserved;
  final double total;
}

class WalletBalance {
  const WalletBalance({required this.label, required this.amount});

  final String label;
  final double amount;
}

class ObligationItem {
  const ObligationItem({
    required this.label,
    required this.dueDate,
    required this.amount,
    required this.status,
  });

  final String label;
  final String dueDate;
  final double amount;
  final String status;
}

class InsightItem {
  const InsightItem({required this.title, required this.body});

  final String title;
  final String body;
}

class FixedIncomeSource {
  const FixedIncomeSource({
    required this.label,
    required this.amount,
    required this.day,
    required this.wallet,
    required this.active,
  });

  final String label;
  final double amount;
  final String day;
  final String wallet;
  final bool active;
}

class CategoryTagSummary {
  const CategoryTagSummary({
    required this.label,
    required this.type,
    required this.trend,
  });

  final String label;
  final String type;
  final String trend;
}

const availablePersonal = 12450.0;
const fixedIncomeExpected = 54000.0;
const fixedIncomeReported = 31200.0;

const bucketSummaries = [
  BucketSummary(label: 'Obligaciones fijas', reserved: 22800, total: 26000),
  BucketSummary(label: 'Personal', reserved: 12450, total: 18000),
  BucketSummary(label: 'Ahorro, inversion y deuda', reserved: 9800, total: 12000),
];

const wallets = [
  WalletBalance(label: 'Efectivo', amount: 6850),
  WalletBalance(label: 'Banco', amount: 22840),
  WalletBalance(label: 'Cooperativa', amount: 9310),
];

const obligations = [
  ObligationItem(label: 'Casa', dueDate: '15 Ago', amount: 12000, status: 'Cubierto'),
  ObligationItem(label: 'Luz', dueDate: '17 Ago', amount: 1850, status: 'Parcial'),
  ObligationItem(label: 'Agua', dueDate: '18 Ago', amount: 740, status: 'Cubierto'),
  ObligationItem(label: 'Netflix', dueDate: '19 Ago', amount: 700, status: 'Pendiente'),
  ObligationItem(label: 'Colegio', dueDate: '20 Ago', amount: 5600, status: 'Pendiente'),
  ObligationItem(label: 'Nomina Mama', dueDate: '21 Ago', amount: 3500, status: 'Cubierto'),
  ObligationItem(label: 'Manutencion', dueDate: '24 Ago', amount: 4200, status: 'Pendiente'),
];

const insights = [
  InsightItem(
    title: 'Delivery por encima de tendencia',
    body: 'Tus gastos en PedidosYa y comidas callejeras estan 28% por encima del promedio movil de 3 meses.',
  ),
  InsightItem(
    title: 'Ajuste posible en ahorro',
    body: 'Si mantienes este ritmo de ingresos, puedes aumentar RD\$1,500 al bucket de ahorro sin afectar tu quincena.',
  ),
  InsightItem(
    title: 'Presupuesto personal bajo control',
    body: 'Vas usando 61% del presupuesto personal con 54% del mes transcurrido.',
  ),
];

const fixedIncomeSources = [
  FixedIncomeSource(
    label: 'Salario principal',
    amount: 40000,
    day: '30 de cada mes',
    wallet: 'Banco',
    active: true,
  ),
  FixedIncomeSource(
    label: 'Comision fija',
    amount: 8000,
    day: '15 de cada mes',
    wallet: 'Banco',
    active: true,
  ),
  FixedIncomeSource(
    label: 'Renta',
    amount: 6000,
    day: '05 de cada mes',
    wallet: 'Cooperativa',
    active: false,
  ),
];

const categorySummaries = [
  CategoryTagSummary(label: 'Casa', type: 'Fija', trend: 'Estable'),
  CategoryTagSummary(label: 'Delivery', type: 'Variable', trend: '+18%'),
  CategoryTagSummary(label: 'Nomina Mama', type: 'Nomina', trend: 'Estable'),
  CategoryTagSummary(label: 'Netflix', type: 'Fija', trend: 'Sin cambios'),
  CategoryTagSummary(label: 'Inversion', type: 'Meta', trend: '+6%'),
];

const quickTags = ['PedidosYa', 'Callejera', 'Oficina', 'Nino', 'Salud', 'Streaming'];