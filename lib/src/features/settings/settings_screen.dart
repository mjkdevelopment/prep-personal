import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/ui/app_card.dart';
import '../../core/utils/formatters.dart';
import '../../domain/models.dart';
import '../../state/app_controller.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String _slugFromLabel(String input) {
    final normalized = input.trim().toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-');
    final compact = normalized.replaceAll(RegExp(r'-{2,}'), '-').replaceAll(RegExp(r'^-|-$'), '');
    return compact.isEmpty ? DateTime.now().microsecondsSinceEpoch.toString() : compact;
  }

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

  List<String> _categoryTypeOptions(CategoryScope scope) {
    return switch (scope) {
      CategoryScope.expense => const ['Fija', 'Variable', 'Meta', 'Nomina'],
      CategoryScope.income => const ['Nomina', 'Trabajo', 'Regalo', 'Intereses', 'Comision', 'Renta', 'Extra'],
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
              Text('Elige cualquier dia del 1 al 31.', style: Theme.of(context).textTheme.bodyMedium),
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
                          border: Border.all(
                            color: selected ? AppColors.petrol : AppColors.sand,
                          ),
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

  Future<void> _showFixedIncomeForm([FixedIncomeSourceModel? source]) async {
    final labelController = TextEditingController(text: source?.label ?? '');
    final amountController = TextEditingController(
      text: source == null ? '' : source.amount.toStringAsFixed(0),
    );
    var expectedDay = source?.expectedDay ?? 15;
    var cadence = source?.cadence ?? FixedIncomeCadence.monthly;
    var expectedWeekday = source?.expectedWeekday ?? DateTime.monday;
    var wallet = source?.wallet ?? walletOptions.first;
    var active = source?.active ?? true;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final navigator = Navigator.of(context);
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
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
                    Text(
                      source == null ? 'Nuevo ingreso fijo' : 'Editar ingreso fijo',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: labelController,
                      decoration: const InputDecoration(labelText: 'Nombre'),
                    ),
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
                            setSheetState(() {
                              expectedDay = picked;
                            });
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
                            setSheetState(() {
                              expectedWeekday = picked;
                            });
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
                      items: walletOptions
                          .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                          .toList(),
                      onChanged: (value) {
                        setSheetState(() {
                          wallet = value ?? wallet;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    SwitchListTile(
                      value: active,
                      title: const Text('Activo en la planeacion'),
                      contentPadding: EdgeInsets.zero,
                      onChanged: (value) {
                        setSheetState(() {
                          active = value;
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () async {
                        final amount = double.tryParse(amountController.text.trim());
                        if (labelController.text.trim().isEmpty || amount == null) {
                          return;
                        }

                        await widget.controller.saveFixedIncome(
                          FixedIncomeSourceModel(
                            id: source?.id,
                            label: labelController.text.trim(),
                            amount: amount,
                            cadence: cadence,
                            expectedDay: expectedDay,
                            expectedWeekday: cadence == FixedIncomeCadence.weekly ? expectedWeekday : null,
                            wallet: wallet,
                            active: active,
                          ),
                        );

                        if (mounted) {
                          navigator.pop();
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            const SnackBar(content: Text('Ingreso fijo guardado')),
                          );
                        }
                      },
                      child: const Text('Guardar ingreso fijo'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _showObligationForm([ObligationModel? source]) async {
    final labelController = TextEditingController(text: source?.label ?? '');
    final amountController = TextEditingController(
      text: source == null ? '' : source.amount.toStringAsFixed(0),
    );
    var dueDay = source?.dueDay ?? 15;
    var cadence = source?.cadence ?? FixedIncomeCadence.monthly;
    var dueWeekday = source?.dueWeekday ?? DateTime.monday;
    var selectedCategory = _initialCategoryForObligation(source);
    var kind = selectedCategory?.type ?? source?.kind ?? 'Fija';
    var status = source?.status ?? 'Pendiente';

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final navigator = Navigator.of(context);
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
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
                    Text(
                      source == null ? 'Nuevo gasto fijo' : 'Editar gasto fijo',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: labelController,
                      decoration: const InputDecoration(labelText: 'Nombre'),
                    ),
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
                        final created = await _showCategoryForm();
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
                      decoration: const InputDecoration(labelText: 'Monto mensual esperado'),
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
                            id: source?.id,
                            label: labelController.text.trim().isEmpty ? 'Gasto' : labelController.text.trim(),
                            amount: amount,
                            categoryId: selectedCategory?.id,
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
                            setSheetState(() {
                              dueDay = picked;
                            });
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
                            setSheetState(() {
                              dueWeekday = picked;
                            });
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
                      onChanged: (value) {
                        setSheetState(() {
                          status = value ?? status;
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () async {
                        final amount = double.tryParse(amountController.text.trim());
                        if (labelController.text.trim().isEmpty || amount == null || selectedCategory == null) {
                          return;
                        }

                        await widget.controller.saveObligation(
                          ObligationModel(
                            id: source?.id,
                            label: labelController.text.trim(),
                            amount: amount,
                            categoryId: selectedCategory!.id,
                            cadence: cadence,
                            dueDay: dueDay,
                            dueWeekday: cadence == FixedIncomeCadence.weekly ? dueWeekday : null,
                            kind: selectedCategory!.type,
                            status: status,
                          ),
                        );

                        if (mounted) {
                          navigator.pop();
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            const SnackBar(content: Text('Gasto fijo guardado')),
                          );
                        }
                      },
                      child: const Text('Guardar gasto fijo'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<CategoryConfig?> _showCategoryForm([CategoryConfig? category, CategoryScope? initialScope]) async {
    final labelController = TextEditingController(text: category?.label ?? '');
    var scope = category?.scope ?? initialScope ?? CategoryScope.expense;
    var type = category?.type ?? _categoryTypeOptions(scope).first;
    var colorToken = category?.colorToken ?? AppVisuals.categoryColorTokens.first;
    var iconToken = category?.iconToken ?? AppVisuals.categoryIconTokens.first;
    var active = category?.active ?? true;

    return showModalBottomSheet<CategoryConfig>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final navigator = Navigator.of(context);
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
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
                    Text(
                      category == null ? 'Nueva categoria' : 'Editar categoria',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: labelController,
                      decoration: const InputDecoration(labelText: 'Nombre visible'),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<CategoryScope>(
                      initialValue: scope,
                      decoration: const InputDecoration(labelText: 'Familia'),
                      items: CategoryScope.values
                          .map((item) => DropdownMenuItem(value: item, child: Text(item.label)))
                          .toList(),
                      onChanged: (value) {
                        if (value == null) {
                          return;
                        }
                        setSheetState(() {
                          scope = value;
                          if (!_categoryTypeOptions(scope).contains(type)) {
                            type = _categoryTypeOptions(scope).first;
                          }
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: type,
                      decoration: const InputDecoration(labelText: 'Tipo'),
                      items: _categoryTypeOptions(scope)
                          .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                          .toList(),
                      onChanged: (value) {
                        setSheetState(() {
                          type = value ?? type;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    Text('Color', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: AppVisuals.categoryColorTokens
                          .map(
                            (token) => _ColorDot(
                              token: token,
                              selected: token == colorToken,
                              onTap: () {
                                setSheetState(() {
                                  colorToken = token;
                                });
                              },
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
                            (token) => _IconChoice(
                              token: token,
                              selected: token == iconToken,
                              onTap: () {
                                setSheetState(() {
                                  iconToken = token;
                                });
                              },
                            ),
                          )
                          .toList(),
                    ),
                    const SizedBox(height: 12),
                    SwitchListTile(
                      value: active,
                      title: const Text('Disponible al registrar transacciones'),
                      contentPadding: EdgeInsets.zero,
                      onChanged: (value) {
                        setSheetState(() {
                          active = value;
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () async {
                        final label = labelController.text.trim();
                        if (label.isEmpty) {
                          return;
                        }

                        final savedCategory = CategoryConfig(
                          id: category?.id ?? _slugFromLabel(label),
                          label: label,
                          scope: scope,
                          type: type,
                          colorToken: colorToken,
                          iconToken: iconToken,
                          active: active,
                        );
                        await widget.controller.saveCategory(savedCategory);

                        if (mounted) {
                          navigator.pop(savedCategory);
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            const SnackBar(content: Text('Categoria guardada')),
                          );
                        }
                      },
                      child: const Text('Guardar categoria'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _showTagForm([TagConfig? tag]) async {
    final labelController = TextEditingController(text: tag?.label ?? '');
    var colorToken = tag?.colorToken ?? AppVisuals.categoryColorTokens.first;
    var active = tag?.active ?? true;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final navigator = Navigator.of(context);
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
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
                    Text(
                      tag == null ? 'Nuevo tag' : 'Editar tag',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: labelController,
                      decoration: const InputDecoration(labelText: 'Nombre visible'),
                    ),
                    const SizedBox(height: 12),
                    Text('Color', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: AppVisuals.categoryColorTokens
                          .map(
                            (token) => _ColorDot(
                              token: token,
                              selected: token == colorToken,
                              onTap: () {
                                setSheetState(() {
                                  colorToken = token;
                                });
                              },
                            ),
                          )
                          .toList(),
                    ),
                    const SizedBox(height: 12),
                    SwitchListTile(
                      value: active,
                      title: const Text('Disponible como tag rapido'),
                      contentPadding: EdgeInsets.zero,
                      onChanged: (value) {
                        setSheetState(() {
                          active = value;
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () async {
                        final label = labelController.text.trim();
                        if (label.isEmpty) {
                          return;
                        }

                        await widget.controller.saveTag(
                          TagConfig(
                            id: tag?.id ?? _slugFromLabel(label),
                            label: label,
                            colorToken: colorToken,
                            active: active,
                          ),
                        );

                        if (mounted) {
                          navigator.pop();
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            const SnackBar(content: Text('Tag guardado')),
                          );
                        }
                      },
                      child: const Text('Guardar tag'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _confirmResetSetup() async {
    final shouldReset = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Reiniciar configuracion inicial'),
          content: const Text(
            'Se borraran ingresos fijos, gastos fijos y transacciones para volver al asistente inicial. Las categorias y tags personalizados se conservan.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Reiniciar'),
            ),
          ],
        );
      },
    );

    if (shouldReset != true) {
      return;
    }

    await widget.controller.resetInitialSetup();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final textTheme = Theme.of(context).textTheme;
        final categories = widget.controller.categoryConfigs;
        final incomeCategories = categories.where((item) => item.scope == CategoryScope.income).toList(growable: false);
        final expenseCategories = categories.where((item) => item.scope == CategoryScope.expense).toList(growable: false);
        final tags = widget.controller.tagConfigs;

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Configuracion financiera', style: textTheme.displaySmall),
              const SizedBox(height: 8),
              Text(
                'Aqui se define la base minima de ingreso, categorias y reglas de planeacion.',
                style: textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              AppCard(
                backgroundColor: const Color(0xFFFFF8EF),
                child: Row(
                  children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        color: AppColors.petrol,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: const Icon(Icons.auto_awesome_rounded, color: Colors.white),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text(
                        'Haz que tus categorias y tags reflejen tu realidad. Colores, iconos y tipos cambian reportes, formularios y lectura rapida.',
                        style: textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Paleta visual', style: textTheme.titleLarge),
                    const SizedBox(height: 8),
                    Text(
                      'El usuario puede cambiar entre cinco ambientes cromaticos sin tocar la logica de la app.',
                      style: textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    ...AppPalettes.all.map(
                      (palette) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: () => widget.controller.saveThemePalette(palette.id),
                          borderRadius: BorderRadius.circular(20),
                          child: Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: widget.controller.selectedPaletteId == palette.id
                                    ? palette.petrol
                                    : AppColors.sand,
                                width: widget.controller.selectedPaletteId == palette.id ? 2 : 1,
                              ),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(palette.name, style: textTheme.titleMedium),
                                      const SizedBox(height: 4),
                                      Text(palette.description, style: textTheme.bodyMedium),
                                      const SizedBox(height: 12),
                                      Row(
                                        children: [
                                          _PaletteDot(color: palette.petrol),
                                          _PaletteDot(color: palette.emerald),
                                          _PaletteDot(color: palette.gold),
                                          _PaletteDot(color: palette.terracotta),
                                          _PaletteDot(color: palette.paper, borderColor: palette.sand),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Icon(
                                  widget.controller.selectedPaletteId == palette.id
                                      ? Icons.radio_button_checked_rounded
                                      : Icons.radio_button_off_rounded,
                                  color: widget.controller.selectedPaletteId == palette.id
                                      ? palette.petrol
                                      : AppColors.slate,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text('Gastos fijos mensuales', style: textTheme.titleLarge),
                        ),
                        TextButton(
                          onPressed: _showObligationForm,
                          child: const Text('Agregar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Define compromisos mensuales y como se reparten si pagas semanal o quincenalmente.',
                      style: textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: _MetricTile(
                            label: 'Total mensual',
                            value: formatCurrency(widget.controller.monthlyFixedOutflowTotal),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _MetricTile(
                            label: 'Apartado quincenal',
                            value: formatCurrency(widget.controller.reservePerQuincena),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    ...widget.controller.obligations.map(
                      (obligation) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: () => _showObligationForm(obligation),
                          borderRadius: BorderRadius.circular(16),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(obligation.label, style: textTheme.titleMedium),
                                      const SizedBox(height: 4),
                                      Text(
                                        '${obligation.scheduleLabel} · ${(widget.controller.categoryById(obligation.categoryId)?.label ?? obligation.kind)}',
                                        style: textTheme.bodyMedium,
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        switch (obligation.cadence) {
                                          FixedIncomeCadence.monthly => 'Pago mensual ${formatCurrency(obligation.installmentExpectedAmount)}',
                                          FixedIncomeCadence.biweekly => '2 pagos de ${formatCurrency(obligation.installmentExpectedAmount)}',
                                          FixedIncomeCadence.weekly => '4 pagos de ${formatCurrency(obligation.installmentExpectedAmount)}',
                                        },
                                        style: textTheme.bodySmall?.copyWith(color: AppColors.slate),
                                      ),
                                    ],
                                  ),
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Text(
                                      formatCurrency(obligation.monthlyExpectedAmount),
                                      style: textTheme.titleMedium,
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      obligation.status,
                                      style: textTheme.labelLarge?.copyWith(
                                        color: obligation.status == 'Cubierto'
                                            ? AppColors.success
                                            : obligation.status == 'Parcial'
                                                ? AppColors.gold
                                                : AppColors.slate,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(width: 8),
                                const Icon(Icons.edit_outlined, size: 18),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text('Ingresos fijos mensuales', style: textTheme.titleLarge),
                        ),
                        TextButton(
                          onPressed: _showFixedIncomeForm,
                          child: const Text('Agregar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Sirven como linea base editable para saber cuanto es lo minimo esperable del mes.',
                      style: textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: _MetricTile(
                            label: 'Esperado',
                            value: formatCurrency(widget.controller.fixedIncomeExpected),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _MetricTile(
                            label: 'Reportado',
                            value: formatCurrency(widget.controller.incomeReportedThisMonth),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    _MetricTile(
                      label: 'Pendiente contra la base',
                      value: formatCurrency(widget.controller.incomeGap),
                    ),
                    const SizedBox(height: 16),
                    ...widget.controller.fixedIncomeSources.map(
                      (source) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: () => _showFixedIncomeForm(source),
                          borderRadius: BorderRadius.circular(16),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(source.label, style: textTheme.titleMedium),
                                      const SizedBox(height: 4),
                                      Text(
                                        '${source.scheduleLabel} · ${source.wallet}',
                                        style: textTheme.bodyMedium,
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        switch (source.cadence) {
                                          FixedIncomeCadence.monthly => 'Pago mensual ${formatCurrency(source.installmentExpectedAmount)}',
                                          FixedIncomeCadence.biweekly => '2 pagos de ${formatCurrency(source.installmentExpectedAmount)}',
                                          FixedIncomeCadence.weekly => '4 pagos de ${formatCurrency(source.installmentExpectedAmount)}',
                                        },
                                        style: textTheme.bodySmall?.copyWith(color: AppColors.slate),
                                      ),
                                    ],
                                  ),
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Text(
                                      formatCurrency(source.monthlyExpectedAmount),
                                      style: textTheme.titleMedium,
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      source.active ? 'Base mensual' : 'Inactivo',
                                      style: textTheme.labelLarge?.copyWith(
                                        color: source.active ? AppColors.success : AppColors.slate,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(width: 8),
                                const Icon(Icons.edit_outlined, size: 18),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Categorias y tags', style: textTheme.titleLarge),
                              const SizedBox(height: 4),
                              Text(
                                'Ahora si son editables y alimentan transacciones, reportes y el radar de gasto.',
                                style: textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(child: Text('Categorias de ingreso', style: textTheme.titleMedium)),
                        TextButton.icon(
                          onPressed: () => _showCategoryForm(null, CategoryScope.income),
                          icon: const Icon(Icons.add_rounded),
                          label: const Text('Agregar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...incomeCategories.map(
                      (category) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: () => _showCategoryForm(category),
                          borderRadius: BorderRadius.circular(18),
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(18),
                            ),
                            child: Row(
                              children: [
                                Container(
                                  width: 42,
                                  height: 42,
                                  decoration: BoxDecoration(
                                    color: AppVisuals.colorFromToken(category.colorToken).withValues(alpha: 0.14),
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  child: Icon(
                                    AppVisuals.iconFromToken(category.iconToken),
                                    color: AppVisuals.colorFromToken(category.colorToken),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(category.label, style: textTheme.titleMedium),
                                      const SizedBox(height: 3),
                                      Text('${category.scope.label} · ${category.type}', style: textTheme.bodyMedium),
                                    ],
                                  ),
                                ),
                                Text(
                                  category.active ? 'Activa' : 'Oculta',
                                  style: textTheme.labelLarge?.copyWith(
                                    color: category.active ? AppColors.success : AppColors.slate,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                const Icon(Icons.edit_outlined, size: 18),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(child: Text('Categorias de gasto', style: textTheme.titleMedium)),
                        TextButton.icon(
                          onPressed: () => _showCategoryForm(),
                          icon: const Icon(Icons.add_rounded),
                          label: const Text('Agregar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...expenseCategories.map(
                      (category) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: () => _showCategoryForm(category),
                          borderRadius: BorderRadius.circular(18),
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(18),
                            ),
                            child: Row(
                              children: [
                                Container(
                                  width: 42,
                                  height: 42,
                                  decoration: BoxDecoration(
                                    color: AppVisuals.colorFromToken(category.colorToken).withValues(alpha: 0.14),
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  child: Icon(
                                    AppVisuals.iconFromToken(category.iconToken),
                                    color: AppVisuals.colorFromToken(category.colorToken),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(category.label, style: textTheme.titleMedium),
                                      const SizedBox(height: 3),
                                      Text('${category.scope.label} · ${category.type}', style: textTheme.bodyMedium),
                                    ],
                                  ),
                                ),
                                Text(
                                  category.active ? 'Activa' : 'Oculta',
                                  style: textTheme.labelLarge?.copyWith(
                                    color: category.active ? AppColors.success : AppColors.slate,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                const Icon(Icons.edit_outlined, size: 18),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(child: Text('Tags rapidos', style: textTheme.titleMedium)),
                        TextButton.icon(
                          onPressed: _showTagForm,
                          icon: const Icon(Icons.add_rounded),
                          label: const Text('Agregar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: tags
                          .map(
                            (tag) => InkWell(
                              onTap: () => _showTagForm(tag),
                              borderRadius: BorderRadius.circular(999),
                              child: Chip(
                                avatar: CircleAvatar(
                                  radius: 9,
                                  backgroundColor: AppVisuals.colorFromToken(tag.colorToken).withValues(alpha: 0.15),
                                  child: Container(
                                    width: 8,
                                    height: 8,
                                    decoration: BoxDecoration(
                                      color: AppVisuals.colorFromToken(tag.colorToken),
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                ),
                                label: Text(tag.label),
                                side: BorderSide(
                                  color: AppVisuals.colorFromToken(tag.colorToken).withValues(alpha: 0.18),
                                ),
                                backgroundColor: Colors.white,
                              ),
                            ),
                          )
                          .toList(),
                    ),
                    const SizedBox(height: 16),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.ivory,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Text(
                        'Tip: si una categoria cambia mucho tu lectura del mes, dejala con color propio y tipo correcto para que el radar de gastos sea mas util.',
                        style: textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              AppCard(
                backgroundColor: const Color(0xFFFFF5F2),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Asistente inicial', style: textTheme.titleLarge),
                    const SizedBox(height: 8),
                    Text(
                      'Si cambiaste de etapa o quieres arrancar desde cero, puedes relanzar el setup guiado y volver a cargar tus datos base.',
                      style: textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _confirmResetSetup,
                      icon: const Icon(Icons.refresh_rounded),
                      label: const Text('Reiniciar configuracion'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _PaletteDot extends StatelessWidget {
  const _PaletteDot({required this.color, this.borderColor});

  final Color color;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 18,
      height: 18,
      margin: const EdgeInsets.only(right: 8),
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: borderColor ?? Colors.transparent),
      ),
    );
  }
}

class _ColorDot extends StatelessWidget {
  const _ColorDot({
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
            width: selected ? 2.4 : 1.2,
          ),
        ),
      ),
    );
  }
}

class _IconChoice extends StatelessWidget {
  const _IconChoice({
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
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: selected ? AppColors.petrol : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.sand),
        ),
        child: Icon(
          AppVisuals.iconFromToken(token),
          color: selected ? Colors.white : AppColors.slate,
        ),
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.ivory,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(value, style: textTheme.titleMedium),
        ],
      ),
    );
  }
}