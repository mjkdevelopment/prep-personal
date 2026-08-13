import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/ui/app_card.dart';
import '../../core/ui/section_header.dart';
import '../../core/utils/formatters.dart';
import '../../domain/models.dart';
import '../../state/app_controller.dart';

class TransactionsScreen extends StatefulWidget {
  const TransactionsScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends State<TransactionsScreen> {
  late final TextEditingController _amountController;
  late final TextEditingController _notesController;
  TransactionKind _selectedKind = TransactionKind.ingreso;
  String _selectedWallet = walletOptions.first;
  String _selectedCategory = '';
  bool _recurring = false;
  final Set<String> _selectedTags = <String>{};

  @override
  void initState() {
    super.initState();
    _amountController = TextEditingController();
    _notesController = TextEditingController();
    _syncSelectedCategory(_categoriesForKind());
    _amountController.addListener(_handleAmountChanged);
  }

  @override
  void dispose() {
    _amountController
      ..removeListener(_handleAmountChanged)
      ..dispose();
    _notesController.dispose();
    super.dispose();
  }

  void _handleAmountChanged() {
    setState(() {});
  }

  double get _parsedAmount => double.tryParse(_amountController.text.trim()) ?? 0;

  List<CategoryConfig> _categoriesForKind() {
    final defaults = _selectedKind == TransactionKind.ingreso
        ? defaultCategoryConfigs.where((item) => item.scope == CategoryScope.income).toList(growable: false)
        : defaultCategoryConfigs.where((item) => item.scope == CategoryScope.expense).toList(growable: false);

    final configured = _selectedKind == TransactionKind.ingreso
        ? widget.controller.activeIncomeCategoryConfigs
        : widget.controller.activeExpenseCategoryConfigs;

    return configured.isNotEmpty ? configured : defaults;
  }

  void _syncSelectedCategory(List<CategoryConfig> categories) {
    if (categories.isEmpty) {
      _selectedCategory = '';
      return;
    }

    if (!categories.any((item) => item.label == _selectedCategory)) {
      _selectedCategory = categories.first.label;
    }
  }

  Future<void> _saveTransaction() async {
    final amount = _parsedAmount;
    if (amount <= 0 || _selectedCategory.isEmpty) {
      return;
    }

    await widget.controller.addTransaction(
      TransactionModel(
        kind: _selectedKind,
        amount: amount,
        wallet: _selectedWallet,
        category: _selectedCategory,
        tags: _selectedTags.toList(),
        notes: _notesController.text.trim(),
        date: DateTime.now(),
        recurring: _recurring,
      ),
    );

    if (!mounted) {
      return;
    }

    _amountController.clear();
    _notesController.clear();
    _selectedTags.clear();
    final resetCategories = widget.controller.activeIncomeCategoryConfigs.isNotEmpty
        ? widget.controller.activeIncomeCategoryConfigs
        : defaultCategoryConfigs.where((item) => item.scope == CategoryScope.income).toList(growable: false);
    setState(() {
      _selectedKind = TransactionKind.ingreso;
      _selectedWallet = walletOptions.first;
      _selectedCategory = resetCategories.isNotEmpty ? resetCategories.first.label : '';
      _recurring = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Transaccion registrada localmente')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final textTheme = Theme.of(context).textTheme;
        final categories = _categoriesForKind();
        _syncSelectedCategory(categories);
        final tags = widget.controller.activeTagConfigs.isNotEmpty
          ? widget.controller.activeTagConfigs
          : defaultTagConfigs;
        final selectedCategory = _selectedCategory;
        final suggestion = widget.controller.suggestionForAmount(_parsedAmount);
        final breaksReserve = _selectedKind != TransactionKind.ingreso &&
            widget.controller.expenseBreaksReserve(_parsedAmount);

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Nueva transaccion', style: textTheme.displaySmall),
              const SizedBox(height: 8),
              Text(
                'Registro rapido con impacto inmediato sobre quincena y presupuesto.',
                style: textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: TransactionKind.values
                    .map(
                      (type) => ChoiceChip(
                        label: Text(type.label),
                        selected: type == _selectedKind,
                        onSelected: (_) {
                          setState(() {
                            _selectedKind = type;
                            final nextCategories = _categoriesForKind();
                            _selectedCategory = nextCategories.isNotEmpty ? nextCategories.first.label : '';
                          });
                        },
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 20),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      controller: _amountController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Monto'),
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      initialValue: _selectedWallet,
                      decoration: const InputDecoration(labelText: 'Cartera'),
                      items: walletOptions
                          .map((wallet) => DropdownMenuItem(value: wallet, child: Text(wallet)))
                          .toList(),
                      onChanged: (value) {
                        setState(() {
                          _selectedWallet = value ?? _selectedWallet;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    if (categories.isNotEmpty)
                      DropdownButtonFormField<String>(
                        initialValue: selectedCategory,
                        decoration: InputDecoration(
                          labelText: _selectedKind == TransactionKind.ingreso
                              ? 'Categoria de ingreso'
                              : 'Categoria de gasto',
                        ),
                        items: categories
                            .map(
                              (category) => DropdownMenuItem(
                                value: category.label,
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                      width: 28,
                                      height: 28,
                                      decoration: BoxDecoration(
                                        color: AppVisuals.colorFromToken(category.colorToken)
                                            .withValues(alpha: 0.16),
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: Icon(
                                        AppVisuals.iconFromToken(category.iconToken),
                                        size: 16,
                                        color: AppVisuals.colorFromToken(category.colorToken),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Text(category.label),
                                  ],
                                ),
                              ),
                            )
                            .toList(),
                        onChanged: (value) {
                          setState(() {
                            _selectedCategory = value ?? selectedCategory;
                          });
                        },
                      )
                    else
                      Text(
                        _selectedKind == TransactionKind.ingreso
                            ? 'No tienes categorias de ingreso activas. Crealas en Ajustes.'
                            : 'No tienes categorias de gasto activas. Crealas en Ajustes.',
                        style: textTheme.bodyMedium,
                      ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _notesController,
                      minLines: 2,
                      maxLines: 4,
                      decoration: const InputDecoration(labelText: 'Notas'),
                    ),
                    const SizedBox(height: 12),
                    SwitchListTile(
                      value: _recurring,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Transaccion recurrente'),
                      onChanged: (value) {
                        setState(() {
                          _recurring = value;
                        });
                      },
                    ),
                    const SizedBox(height: 8),
                    Text('Tags rapidos', style: textTheme.titleMedium),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: tags
                          .map(
                            (tag) => FilterChip(
                              avatar: CircleAvatar(
                                radius: 9,
                                backgroundColor:
                                    AppVisuals.colorFromToken(tag.colorToken).withValues(alpha: 0.14),
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
                              selected: _selectedTags.contains(tag.label),
                              onSelected: (selected) {
                                setState(() {
                                  if (selected) {
                                    _selectedTags.add(tag.label);
                                  } else {
                                    _selectedTags.remove(tag.label);
                                  }
                                });
                              },
                            ),
                          )
                          .toList(),
                    ),
                    if (_selectedKind == TransactionKind.ingreso) ...[
                      const SizedBox(height: 18),
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.ivory,
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Distribucion sugerida para este ingreso', style: textTheme.titleMedium),
                            const SizedBox(height: 12),
                            _DistributionRow(label: 'Obligaciones', amount: suggestion.forObligations),
                            _DistributionRow(label: 'Ahorro, inversion y deuda', amount: suggestion.forGoals),
                            _DistributionRow(label: 'Disponible personal de este ingreso', amount: suggestion.forPersonal),
                            _DistributionRow(
                              label: 'Disponible personal acumulado del mes',
                              amount: widget.controller.remainingPersonalRecommendedThisMonth,
                            ),
                            const SizedBox(height: 8),
                            Text(suggestion.rationale, style: textTheme.bodyMedium),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Contexto de registro',
                subtitle: 'La advertencia cambia segun el impacto sobre tu reserva.',
              ),
              const SizedBox(height: 16),
              if (breaksReserve)
                AppCard(
                  backgroundColor: const Color(0xFFFFF6E8),
                  child: Row(
                    children: [
                      Icon(Icons.warning_amber_rounded, color: AppColors.warning),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Este movimiento compromete la reserva de quincena. El disponible personal recomendado restante es ${formatCurrency(widget.controller.remainingPersonalRecommendedThisMonth)}.',
                          style: textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                )
              else
                AppCard(
                  backgroundColor: const Color(0xFFF2F7F2),
                  child: Text(
                    'El registro respeta la logica base del plan actual. Disponible personal recomendado restante: ${formatCurrency(widget.controller.remainingPersonalRecommendedThisMonth)}.',
                    style: textTheme.bodyMedium,
                  ),
                ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _parsedAmount > 0 ? _saveTransaction : null,
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(56)),
                child: const Text('Registrar transaccion'),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _DistributionRow extends StatelessWidget {
  const _DistributionRow({required this.label, required this.amount});

  final String label;
  final double amount;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(child: Text(label, style: textTheme.bodyMedium)),
          Text(formatCurrency(amount), style: textTheme.titleMedium),
        ],
      ),
    );
  }
}