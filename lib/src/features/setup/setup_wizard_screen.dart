import 'package:flutter/material.dart';

import '../../core/app_identity.dart';
import '../../core/theme/app_theme.dart';
import '../../core/ui/app_card.dart';
import '../../core/utils/formatters.dart';
import '../../domain/models.dart';
import '../../state/app_controller.dart';

class SetupWizardScreen extends StatefulWidget {
  const SetupWizardScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<SetupWizardScreen> createState() => _SetupWizardScreenState();
}

class _SetupWizardScreenState extends State<SetupWizardScreen> {
  int _stepIndex = 0;
  bool _saving = false;
  final List<FixedIncomeSourceModel> _fixedIncomes = [];
  final List<ObligationModel> _obligations = [];

  String _slugFromLabel(String input) {
    final normalized = input.trim().toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-');
    final compact = normalized.replaceAll(RegExp(r'-{2,}'), '-').replaceAll(RegExp(r'^-|-$'), '');
    return compact.isEmpty ? DateTime.now().microsecondsSinceEpoch.toString() : compact;
  }

  @override
  void initState() {
    super.initState();
    _fixedIncomes.addAll(widget.controller.fixedIncomeSources);
    _obligations.addAll(widget.controller.obligations);
  }

  double get _incomeBaseTotal =>
      _fixedIncomes.where((item) => item.active).fold<double>(0, (sum, item) => sum + item.monthlyExpectedAmount);

  double get _obligationTotal => _obligations.fold<double>(0, (sum, item) => sum + item.amount);

  String _amountLabelForCadence(FixedIncomeCadence cadence) {
    return 'Monto mensual esperado';
  }

  String _projectionHintForCadence(FixedIncomeCadence cadence) {
    return switch (cadence) {
      FixedIncomeCadence.monthly => 'Se registra como un solo pago mensual.',
      FixedIncomeCadence.biweekly => 'El monto mensual se divide en dos pagos: dia 15 y dia 30.',
      FixedIncomeCadence.weekly => 'El monto mensual se divide en cuatro pagos semanales.',
    };
  }

  String _obligationProjectionHintForCadence(FixedIncomeCadence cadence) {
    return switch (cadence) {
      FixedIncomeCadence.monthly => 'Se registra como un compromiso mensual único.',
      FixedIncomeCadence.biweekly => 'El gasto mensual se divide en dos pagos: dia 15 y dia 30.',
      FixedIncomeCadence.weekly => 'El gasto mensual se divide en cuatro pagos semanales.',
    };
  }

  CategoryConfig? _initialCategoryForObligation(ObligationModel? source) {
    final categories = widget.controller.activeExpenseCategoryConfigs.isNotEmpty
        ? widget.controller.activeExpenseCategoryConfigs
        : defaultCategoryConfigs.where((item) => item.scope == CategoryScope.expense).toList(growable: false);
    if (categories.isEmpty) {
      return null;
    }

    final byId = widget.controller.categoryById(source?.categoryId);
    if (byId != null) {
      return byId;
    }

    if (source != null) {
      final byLabel = widget.controller.categoryForLabel(source.label);
      if (byLabel != null) {
        return byLabel;
      }

      for (final category in categories) {
        if (category.type == source.kind) {
          return category;
        }
      }
    }

    return categories.first;
  }

  Future<CategoryConfig?> _showWizardCategoryCreator() async {
    final labelController = TextEditingController();
    var type = 'Fija';
    var colorToken = AppVisuals.categoryColorTokens.first;
    var iconToken = AppVisuals.categoryIconTokens.first;

    return showModalBottomSheet<CategoryConfig>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        final navigator = Navigator.of(context);
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return _WizardSheet(
              title: 'Crear categoria para este gasto',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: labelController,
                    decoration: const InputDecoration(labelText: 'Nombre de la categoria'),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: type,
                    decoration: const InputDecoration(labelText: 'Tipo'),
                    items: const ['Fija', 'Variable', 'Meta', 'Nomina']
                        .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                        .toList(),
                    onChanged: (value) => setSheetState(() => type = value ?? type),
                  ),
                  const SizedBox(height: 12),
                  Text('Color', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: AppVisuals.categoryColorTokens
                        .map(
                          (token) => _WizardColorDot(
                            token: token,
                            selected: token == colorToken,
                            onTap: () => setSheetState(() => colorToken = token),
                          ),
                        )
                        .toList(),
                  ),
                  const SizedBox(height: 14),
                  Text('Icono', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: AppVisuals.categoryIconTokens
                        .map(
                          (token) => _WizardIconChoice(
                            token: token,
                            selected: token == iconToken,
                            onTap: () => setSheetState(() => iconToken = token),
                          ),
                        )
                        .toList(),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () async {
                      final label = labelController.text.trim();
                      if (label.isEmpty) {
                        return;
                      }

                      final category = CategoryConfig(
                        id: _slugFromLabel(label),
                        label: label,
                        scope: CategoryScope.expense,
                        type: type,
                        colorToken: colorToken,
                        iconToken: iconToken,
                      );
                      await widget.controller.saveCategory(category);
                      if (mounted) {
                        setState(() {});
                        navigator.pop(category);
                      }
                    },
                    child: const Text('Crear categoria'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<int?> _showDayPicker({required int initialDay, required String title}) async {
    return showModalBottomSheet<int>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
          ),
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 48,
                  height: 5,
                  decoration: BoxDecoration(
                    color: AppColors.sand,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 6),
              Text('Escoge cualquier dia del 1 al 31.', style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 18),
              Flexible(
                child: GridView.builder(
                  shrinkWrap: true,
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 4,
                    mainAxisSpacing: 10,
                    crossAxisSpacing: 10,
                    childAspectRatio: 1.4,
                  ),
                  itemCount: 31,
                  itemBuilder: (context, index) {
                    final day = index + 1;
                    final selected = day == initialDay;
                    return InkWell(
                      onTap: () => Navigator.of(context).pop(day),
                      borderRadius: BorderRadius.circular(18),
                      child: Container(
                        decoration: BoxDecoration(
                          color: selected ? AppColors.petrol : AppColors.ivory,
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(color: selected ? AppColors.petrol : AppColors.sand),
                        ),
                        child: Center(
                          child: Text(
                            '$day',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  color: selected ? Colors.white : AppColors.ink,
                                ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<int?> _showWeekdayPicker({required int initialWeekday, required String title}) async {
    const weekdays = [
      DateTime.monday,
      DateTime.tuesday,
      DateTime.wednesday,
      DateTime.thursday,
      DateTime.friday,
      DateTime.saturday,
      DateTime.sunday,
    ];

    return showModalBottomSheet<int>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
          ),
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 48,
                  height: 5,
                  decoration: BoxDecoration(
                    color: AppColors.sand,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 6),
              Text('Elige el dia de la semana en que normalmente recibes ese ingreso.', style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 18),
              ...weekdays.map(
                (weekday) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: InkWell(
                    onTap: () => Navigator.of(context).pop(weekday),
                    borderRadius: BorderRadius.circular(18),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      decoration: BoxDecoration(
                        color: weekday == initialWeekday ? AppColors.petrol : AppColors.ivory,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                          color: weekday == initialWeekday ? AppColors.petrol : AppColors.sand,
                        ),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              weekday.weekdayLabel,
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    color: weekday == initialWeekday ? Colors.white : AppColors.ink,
                                  ),
                            ),
                          ),
                          if (weekday == initialWeekday)
                            const Icon(Icons.check_rounded, color: Colors.white),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _showIncomeEditor([FixedIncomeSourceModel? source, int? index]) async {
    final labelController = TextEditingController(text: source?.label ?? '');
    final amountController = TextEditingController(text: source == null ? '' : source.amount.toStringAsFixed(0));
    var expectedDay = source?.expectedDay ?? 15;
    var cadence = source?.cadence ?? FixedIncomeCadence.monthly;
    var expectedWeekday = source?.expectedWeekday ?? DateTime.monday;
    var wallet = source?.wallet ?? walletOptions.first;
    var active = source?.active ?? true;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return _WizardSheet(
              title: source == null ? 'Agregar ingreso fijo' : 'Editar ingreso fijo',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(controller: labelController, decoration: const InputDecoration(labelText: 'Nombre del ingreso')),
                  const SizedBox(height: 12),
                  TextField(
                    controller: amountController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(labelText: _amountLabelForCadence(cadence)),
                  ),
                  const SizedBox(height: 12),
                  Text('Frecuencia esperada', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: FixedIncomeCadence.values.map((option) {
                      return ChoiceChip(
                        label: Text(option.label),
                        selected: cadence == option,
                        onSelected: (_) {
                          setSheetState(() {
                            cadence = option;
                            if (cadence == FixedIncomeCadence.biweekly) {
                              expectedDay = 15;
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _projectionHintForCadence(cadence),
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (amountController.text.trim().isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      () {
                        final amount = double.tryParse(amountController.text.trim());
                        if (amount == null) {
                          return 'Ingresa un monto mensual valido para ver el reparto.';
                        }
                        final monthlyModel = FixedIncomeSourceModel(
                          label: labelController.text.trim().isEmpty ? 'Ingreso' : labelController.text.trim(),
                          amount: amount,
                          cadence: cadence,
                          expectedDay: expectedDay,
                          expectedWeekday: expectedWeekday,
                          wallet: wallet,
                          active: active,
                        );
                        return switch (cadence) {
                          FixedIncomeCadence.monthly => 'Se espera ${formatCurrency(monthlyModel.installmentExpectedAmount)} una vez al mes.',
                          FixedIncomeCadence.biweekly => 'Se esperan 2 pagos de ${formatCurrency(monthlyModel.installmentExpectedAmount)} cada mes.',
                          FixedIncomeCadence.weekly => 'Se esperan 4 pagos de ${formatCurrency(monthlyModel.installmentExpectedAmount)} cada mes.',
                        };
                      }(),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.petrol),
                    ),
                  ],
                  const SizedBox(height: 12),
                  if (cadence == FixedIncomeCadence.monthly)
                    InkWell(
                      onTap: () async {
                        final picked = await _showDayPicker(
                          initialDay: expectedDay,
                          title: 'Dia esperado del ingreso mensual',
                        );
                        if (picked != null) {
                          setSheetState(() => expectedDay = picked);
                        }
                      },
                      borderRadius: BorderRadius.circular(18),
                      child: InputDecorator(
                        decoration: const InputDecoration(labelText: 'Dia esperado del mes'),
                        child: Row(
                          children: [
                            const Icon(Icons.calendar_month_rounded, size: 18),
                            const SizedBox(width: 10),
                            Expanded(child: Text('Dia $expectedDay')),
                            const Icon(Icons.expand_more_rounded),
                          ],
                        ),
                      ),
                    ),
                  if (cadence == FixedIncomeCadence.weekly)
                    InkWell(
                      onTap: () async {
                        final picked = await _showWeekdayPicker(
                          initialWeekday: expectedWeekday,
                          title: 'Dia esperado del ingreso semanal',
                        );
                        if (picked != null) {
                          setSheetState(() => expectedWeekday = picked);
                        }
                      },
                      borderRadius: BorderRadius.circular(18),
                      child: InputDecorator(
                        decoration: const InputDecoration(labelText: 'Dia de la semana'),
                        child: Row(
                          children: [
                            const Icon(Icons.view_week_rounded, size: 18),
                            const SizedBox(width: 10),
                            Expanded(child: Text(expectedWeekday.weekdayLabel)),
                            const Icon(Icons.expand_more_rounded),
                          ],
                        ),
                      ),
                    ),
                  if (cadence == FixedIncomeCadence.biweekly)
                    InputDecorator(
                      decoration: const InputDecoration(labelText: 'Fechas aplicadas'),
                      child: Row(
                        children: [
                          const Icon(Icons.event_repeat_rounded, size: 18),
                          const SizedBox(width: 10),
                          Expanded(child: Text('Dias 15 y 30 de cada mes')),
                        ],
                      ),
                    ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: wallet,
                    decoration: const InputDecoration(labelText: 'Cartera destino'),
                    items: walletOptions.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                    onChanged: (value) => setSheetState(() => wallet = value ?? wallet),
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    value: active,
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Contar este ingreso en la base mensual'),
                    onChanged: (value) => setSheetState(() => active = value),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () {
                      final label = labelController.text.trim();
                      final amount = double.tryParse(amountController.text.trim());
                      if (label.isEmpty || amount == null || amount <= 0) {
                        return;
                      }

                      final item = FixedIncomeSourceModel(
                        id: source?.id,
                        label: label,
                        amount: amount,
                        cadence: cadence,
                        expectedDay: expectedDay,
                        expectedWeekday: cadence == FixedIncomeCadence.weekly ? expectedWeekday : null,
                        wallet: wallet,
                        active: active,
                      );
                      setState(() {
                        if (index == null) {
                          _fixedIncomes.add(item);
                        } else {
                          _fixedIncomes[index] = item;
                        }
                      });
                      Navigator.of(context).pop();
                    },
                    child: const Text('Guardar ingreso'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _showObligationEditor([ObligationModel? source, int? index]) async {
    final labelController = TextEditingController(text: source?.label ?? '');
    final amountController = TextEditingController(text: source == null ? '' : source.amount.toStringAsFixed(0));
    var dueDay = source?.dueDay ?? 15;
    var cadence = source?.cadence ?? FixedIncomeCadence.monthly;
    var dueWeekday = source?.dueWeekday ?? DateTime.monday;
    var selectedCategory = _initialCategoryForObligation(source);
    var kind = selectedCategory?.type ?? source?.kind ?? 'Fija';
    var status = source?.status ?? 'Pendiente';

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return _WizardSheet(
              title: source == null ? 'Agregar gasto fijo' : 'Editar gasto fijo',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(controller: labelController, decoration: const InputDecoration(labelText: 'Nombre del gasto')),
                  const SizedBox(height: 12),
                  Text('Categoria', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 10),
                  if (widget.controller.activeExpenseCategoryConfigs.isNotEmpty)
                    DropdownButtonFormField<String>(
                      initialValue: selectedCategory?.id,
                      decoration: const InputDecoration(labelText: 'Pertenece a esta categoria'),
                      items: widget.controller.activeExpenseCategoryConfigs
                          .map(
                            (category) => DropdownMenuItem(
                              value: category.id,
                              child: Row(
                                children: [
                                  Container(
                                    width: 30,
                                    height: 30,
                                    decoration: BoxDecoration(
                                      color: AppVisuals.colorFromToken(category.colorToken).withValues(alpha: 0.14),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Icon(
                                      AppVisuals.iconFromToken(category.iconToken),
                                      size: 16,
                                      color: AppVisuals.colorFromToken(category.colorToken),
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(child: Text(category.label)),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        setSheetState(() {
                          selectedCategory = widget.controller.categoryById(value);
                          kind = selectedCategory?.type ?? kind;
                        });
                      },
                    )
                  else
                    Text(
                      'Todavia no tienes categorias activas. Crea una para este gasto.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () async {
                      final created = await _showWizardCategoryCreator();
                      if (created != null) {
                        setSheetState(() {
                          selectedCategory = created;
                          kind = created.type;
                        });
                      }
                    },
                    icon: const Icon(Icons.add_circle_outline_rounded),
                    label: const Text('Crear categoria nueva'),
                  ),
                  if (selectedCategory != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: AppColors.sand),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 42,
                            height: 42,
                            decoration: BoxDecoration(
                              color: AppVisuals.colorFromToken(selectedCategory!.colorToken).withValues(alpha: 0.14),
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: Icon(
                              AppVisuals.iconFromToken(selectedCategory!.iconToken),
                              color: AppVisuals.colorFromToken(selectedCategory!.colorToken),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(selectedCategory!.label, style: Theme.of(context).textTheme.titleMedium),
                                const SizedBox(height: 4),
                                Text(selectedCategory!.type, style: Theme.of(context).textTheme.bodyMedium),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 12),
                  TextField(
                    controller: amountController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Monto mensual'),
                  ),
                  const SizedBox(height: 12),
                  Text('Frecuencia del gasto', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: FixedIncomeCadence.values.map((option) {
                      return ChoiceChip(
                        label: Text(option.label),
                        selected: cadence == option,
                        onSelected: (_) {
                          setSheetState(() {
                            cadence = option;
                            if (cadence == FixedIncomeCadence.biweekly) {
                              dueDay = 15;
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _obligationProjectionHintForCadence(cadence),
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (amountController.text.trim().isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      () {
                        final amount = double.tryParse(amountController.text.trim());
                        if (amount == null) {
                          return 'Ingresa un monto mensual valido para ver el reparto.';
                        }
                        final monthlyModel = ObligationModel(
                          label: labelController.text.trim().isEmpty ? 'Gasto' : labelController.text.trim(),
                          amount: amount,
                          cadence: cadence,
                          dueDay: dueDay,
                          dueWeekday: dueWeekday,
                          kind: kind,
                          status: status,
                        );
                        return switch (cadence) {
                          FixedIncomeCadence.monthly => 'Se espera ${formatCurrency(monthlyModel.installmentExpectedAmount)} una vez al mes.',
                          FixedIncomeCadence.biweekly => 'Se esperan 2 pagos de ${formatCurrency(monthlyModel.installmentExpectedAmount)} cada mes.',
                          FixedIncomeCadence.weekly => 'Se esperan 4 pagos de ${formatCurrency(monthlyModel.installmentExpectedAmount)} cada mes.',
                        };
                      }(),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.petrol),
                    ),
                  ],
                  const SizedBox(height: 12),
                  if (cadence == FixedIncomeCadence.monthly)
                    InkWell(
                      onTap: () async {
                        final picked = await _showDayPicker(
                          initialDay: dueDay,
                          title: 'Dia de vencimiento mensual',
                        );
                        if (picked != null) {
                          setSheetState(() => dueDay = picked);
                        }
                      },
                      borderRadius: BorderRadius.circular(18),
                      child: InputDecorator(
                        decoration: const InputDecoration(labelText: 'Dia de vencimiento'),
                        child: Row(
                          children: [
                            const Icon(Icons.calendar_today_rounded, size: 18),
                            const SizedBox(width: 10),
                            Expanded(child: Text('Dia $dueDay')),
                            const Icon(Icons.expand_more_rounded),
                          ],
                        ),
                      ),
                    ),
                  if (cadence == FixedIncomeCadence.weekly)
                    InkWell(
                      onTap: () async {
                        final picked = await _showWeekdayPicker(
                          initialWeekday: dueWeekday,
                          title: 'Dia del gasto semanal',
                        );
                        if (picked != null) {
                          setSheetState(() => dueWeekday = picked);
                        }
                      },
                      borderRadius: BorderRadius.circular(18),
                      child: InputDecorator(
                        decoration: const InputDecoration(labelText: 'Dia de la semana'),
                        child: Row(
                          children: [
                            const Icon(Icons.view_week_rounded, size: 18),
                            const SizedBox(width: 10),
                            Expanded(child: Text(dueWeekday.weekdayLabel)),
                            const Icon(Icons.expand_more_rounded),
                          ],
                        ),
                      ),
                    ),
                  if (cadence == FixedIncomeCadence.biweekly)
                    InputDecorator(
                      decoration: const InputDecoration(labelText: 'Fechas aplicadas'),
                      child: Row(
                        children: [
                          const Icon(Icons.event_repeat_rounded, size: 18),
                          const SizedBox(width: 10),
                          Expanded(child: Text('Dias 15 y 30 de cada mes')),
                        ],
                      ),
                    ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: status,
                    decoration: const InputDecoration(labelText: 'Estado inicial'),
                    items: const ['Pendiente', 'Parcial', 'Cubierto']
                        .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                        .toList(),
                    onChanged: (value) => setSheetState(() => status = value ?? status),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () {
                      final label = labelController.text.trim();
                      final amount = double.tryParse(amountController.text.trim());
                      if (label.isEmpty || amount == null || amount <= 0 || selectedCategory == null) {
                        return;
                      }

                      final item = ObligationModel(
                        id: source?.id,
                        label: label,
                        amount: amount,
                        categoryId: selectedCategory!.id,
                        cadence: cadence,
                        dueDay: dueDay,
                        dueWeekday: cadence == FixedIncomeCadence.weekly ? dueWeekday : null,
                        kind: selectedCategory!.type,
                        status: status,
                      );
                      setState(() {
                        if (index == null) {
                          _obligations.add(item);
                        } else {
                          _obligations[index] = item;
                        }
                      });
                      Navigator.of(context).pop();
                    },
                    child: const Text('Guardar gasto fijo'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _complete() async {
    if (_fixedIncomes.isEmpty) {
      return;
    }

    setState(() => _saving = true);
    await widget.controller.completeInitialSetup(
      fixedIncomes: _fixedIncomes,
      obligations: _obligations,
    );
    if (mounted) {
      setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: AppColors.ivory,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned(
              top: -40,
              right: -20,
              child: Container(
                width: 180,
                height: 180,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [AppColors.gold.withValues(alpha: 0.18), AppColors.coral.withValues(alpha: 0.02)],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
              ),
            ),
            Positioned(
              top: 120,
              left: -36,
              child: Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.sky.withValues(alpha: 0.10),
                ),
              ),
            ),
            SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _WizardHero(
                    stepIndex: _stepIndex,
                    incomeBaseTotal: _incomeBaseTotal,
                    obligationTotal: _obligationTotal,
                  ),
                  const SizedBox(height: 22),
                  _WizardRail(stepIndex: _stepIndex),
                  const SizedBox(height: 20),
                  if (_stepIndex == 0) ...[
                    _SummaryCallout(
                      title: 'Ingresos cargados',
                      body: _fixedIncomes.isEmpty
                          ? 'Todavia no agregas ingresos fijos.'
                          : 'Base esperada: ${formatCurrency(_incomeBaseTotal)}.',
                    ),
                    const SizedBox(height: 16),
                    ..._fixedIncomes.asMap().entries.map(
                      (entry) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _EditableRow(
                          title: entry.value.label,
                          subtitle: '${entry.value.scheduleLabel} · ${entry.value.wallet}',
                          amount: formatCurrency(entry.value.monthlyExpectedAmount),
                          onTap: () {
                            _showIncomeEditor(entry.value, entry.key);
                          },
                          onDelete: () => setState(() => _fixedIncomes.removeAt(entry.key)),
                        ),
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () {
                        _showIncomeEditor();
                      },
                      icon: const Icon(Icons.add_rounded),
                      label: const Text('Agregar ingreso fijo'),
                    ),
                  ] else if (_stepIndex == 1) ...[
                    _SummaryCallout(
                      title: 'Gastos fijos cargados',
                      body: _obligations.isEmpty
                          ? 'Puedes empezar sin gastos fijos y agregarlos luego, pero el calculo quincenal sera mas util si los defines ahora.'
                          : 'Total mensual fijo: ${formatCurrency(_obligationTotal)}.',
                    ),
                    const SizedBox(height: 16),
                    ..._obligations.asMap().entries.map(
                      (entry) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _EditableRow(
                          title: entry.value.label,
                          subtitle: '${entry.value.scheduleLabel} · ${(widget.controller.categoryById(entry.value.categoryId)?.label ?? entry.value.kind)}',
                          amount: formatCurrency(entry.value.monthlyExpectedAmount),
                          onTap: () {
                            _showObligationEditor(entry.value, entry.key);
                          },
                          onDelete: () => setState(() => _obligations.removeAt(entry.key)),
                        ),
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () {
                        _showObligationEditor();
                      },
                      icon: const Icon(Icons.add_rounded),
                      label: const Text('Agregar gasto fijo'),
                    ),
                  ] else ...[
                    AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Resumen de activacion', style: textTheme.titleLarge),
                          const SizedBox(height: 16),
                          _ResumeLine(label: 'Ingresos fijos', value: '${_fixedIncomes.length} cargados'),
                          _ResumeLine(label: 'Base mensual esperada', value: formatCurrency(_incomeBaseTotal)),
                          _ResumeLine(label: 'Gastos fijos', value: '${_obligations.length} cargados'),
                          _ResumeLine(label: 'Apartado quincenal base', value: formatCurrency(_obligationTotal / 2)),
                          const SizedBox(height: 14),
                          Text(
                            'Al finalizar, dejo limpio el historial demo y activo la app con tus datos reales. Categorias y tags quedan editables luego en Ajustes.',
                            style: textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      if (_stepIndex > 0)
                        Expanded(
                          child: OutlinedButton(
                            onPressed: _saving ? null : () => setState(() => _stepIndex -= 1),
                            child: const Text('Atras'),
                          ),
                        ),
                      if (_stepIndex > 0) const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          onPressed: _saving
                              ? null
                              : _stepIndex == 2
                                  ? _complete
                                  : () {
                                      if (_stepIndex == 0 && _fixedIncomes.isEmpty) {
                                        return;
                                      }
                                      setState(() => _stepIndex += 1);
                                    },
                          child: Text(_saving ? 'Guardando...' : _stepIndex == 2 ? 'Activar Gride Ledger' : 'Continuar'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WizardSheet extends StatelessWidget {
  const _WizardSheet({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
      ),
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            child,
          ],
        ),
      ),
    );
  }
}

class _WizardColorDot extends StatelessWidget {
  const _WizardColorDot({
    required this.token,
    required this.selected,
    required this.onTap,
  });

  final String token;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = AppVisuals.colorFromToken(token);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          border: Border.all(
            color: selected ? AppColors.ink : Colors.white,
            width: selected ? 3 : 1,
          ),
        ),
      ),
    );
  }
}

class _WizardIconChoice extends StatelessWidget {
  const _WizardIconChoice({
    required this.token,
    required this.selected,
    required this.onTap,
  });

  final String token;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: selected ? AppColors.petrol : AppColors.ivory,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: selected ? AppColors.petrol : AppColors.sand),
        ),
        child: Icon(
          AppVisuals.iconFromToken(token),
          size: 20,
          color: selected ? Colors.white : AppColors.ink,
        ),
      ),
    );
  }
}

class _WizardHero extends StatelessWidget {
  const _WizardHero({
    required this.stepIndex,
    required this.incomeBaseTotal,
    required this.obligationTotal,
  });

  final int stepIndex;
  final double incomeBaseTotal;
  final double obligationTotal;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppColors.petrol, AppColors.emerald, AppColors.sky.withValues(alpha: 0.92)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(
            color: AppColors.petrol.withValues(alpha: 0.22),
            blurRadius: 36,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
                ),
                child: const Icon(Icons.auto_graph_rounded, color: Colors.white),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(appDisplayName, style: textTheme.labelLarge?.copyWith(color: AppColors.sand)),
                    const SizedBox(height: 4),
                    Text('Setup inmersivo de bienvenida', style: textTheme.titleLarge?.copyWith(color: Colors.white)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 22),
          Text(
            stepIndex == 0
                ? 'Define tu linea base de ingresos'
                : stepIndex == 1
                    ? 'Construye tu mapa de obligaciones'
                    : 'Activa tu tablero real',
            style: textTheme.displaySmall?.copyWith(color: Colors.white, fontSize: 38),
          ),
          const SizedBox(height: 12),
          Text(
            stepIndex == 0
                ? 'Lo primero que debe ver Gride Ledger es cuanto suele entrar cada mes y en que fechas lo esperas.'
                : stepIndex == 1
                    ? 'Ahora mapeamos los fijos para que la lectura quincenal y el disponible personal sean confiables.'
                    : 'Revisa la fotografia de arranque antes de entrar a la app completa.',
            style: textTheme.bodyLarge?.copyWith(color: Colors.white.withValues(alpha: 0.86)),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(child: _HeroMetric(label: 'Base ingresos', value: formatCurrency(incomeBaseTotal))),
              const SizedBox(width: 12),
              Expanded(child: _HeroMetric(label: 'Fijos mensuales', value: formatCurrency(obligationTotal))),
            ],
          ),
        ],
      ),
    );
  }
}

class _WizardRail extends StatelessWidget {
  const _WizardRail({required this.stepIndex});

  final int stepIndex;

  @override
  Widget build(BuildContext context) {
    final titles = ['Ingresos', 'Compromisos', 'Activacion'];

    return Row(
      children: List.generate(titles.length, (index) {
        final active = index == stepIndex;
        final done = index < stepIndex;
        return Expanded(
          child: Container(
            margin: EdgeInsets.only(right: index == titles.length - 1 ? 0 : 10),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: active ? Colors.white : AppColors.paper.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: done || active ? AppColors.petrol : AppColors.sand),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 14,
                  backgroundColor: done || active ? AppColors.petrol : AppColors.sand,
                  child: Icon(
                    done ? Icons.check_rounded : Icons.circle,
                    size: done ? 16 : 10,
                    color: done || active ? Colors.white : AppColors.slate,
                  ),
                ),
                const SizedBox(height: 10),
                Text(titles[index], style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
          ),
        );
      }),
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.white70)),
          const SizedBox(height: 5),
          Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white)),
        ],
      ),
    );
  }
}

class _SummaryCallout extends StatelessWidget {
  const _SummaryCallout({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      backgroundColor: const Color(0xFFFFF8EF),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(body, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _EditableRow extends StatelessWidget {
  const _EditableRow({
    required this.title,
    required this.subtitle,
    required this.amount,
    required this.onTap,
    required this.onDelete,
  });

  final String title;
  final String subtitle;
  final String amount;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Row(
        children: [
          Expanded(
            child: InkWell(
              onTap: onTap,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(amount, style: Theme.of(context).textTheme.titleMedium),
              Row(
                children: [
                  IconButton(onPressed: onTap, icon: const Icon(Icons.edit_outlined)),
                  IconButton(onPressed: onDelete, icon: const Icon(Icons.delete_outline_rounded)),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ResumeLine extends StatelessWidget {
  const _ResumeLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(child: Text(label, style: Theme.of(context).textTheme.bodyMedium)),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}