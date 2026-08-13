import 'package:flutter/material.dart';

import '../../core/app_identity.dart';
import '../../core/theme/app_theme.dart';
import '../../core/ui/app_card.dart';
import '../../core/ui/section_header.dart';
import '../../core/utils/formatters.dart';
import '../../domain/models.dart';
import '../../state/app_controller.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final textTheme = Theme.of(context).textTheme;
        final expenseComparisons = controller.expenseComparisons;
        final highestExpense = expenseComparisons.fold<double>(
          1,
          (maxValue, item) => [maxValue, item.currentAmount, item.previousAmount].reduce(
            (left, right) => left > right ? left : right,
          ),
        );

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(appDisplayName, style: textTheme.bodyMedium),
              const SizedBox(height: 8),
              Text('Disponible para hoy', style: textTheme.displaySmall),
              const SizedBox(height: 8),
              Text(
                'La app prioriza quincena, obligaciones y metas antes de liberar gasto personal.',
                style: textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              AppCard(
                backgroundColor: AppColors.petrol,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: const Icon(Icons.account_balance_wallet_rounded, color: Colors.white),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          'Disponible personal recomendado',
                          style: textTheme.labelLarge?.copyWith(color: AppColors.sand),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(
                      formatCurrency(controller.safePersonalAvailable),
                      style: textTheme.displaySmall?.copyWith(color: Colors.white),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Ingreso reportado ${formatCurrency(controller.incomeReportedThisMonth)} frente a esperado ${formatCurrency(controller.fixedIncomeExpected)}.',
                      style: textTheme.bodyMedium?.copyWith(color: Colors.white70),
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: _HeroStat(
                            label: 'Gasto del mes',
                            value: formatCurrency(controller.currentMonthExpenseTotal),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _HeroStat(
                            label: 'Meta quincenal',
                            value: formatCurrency(controller.reservePerQuincena),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Reserva quincenal',
                subtitle: 'Cuanto apartar por quincena a partir del total fijo mensual.',
              ),
              const SizedBox(height: 16),
              AppCard(
                backgroundColor: const Color(0xFFFFF8EF),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _ReserveMetric(
                            label: 'Fijo mensual',
                            value: formatCurrency(controller.monthlyFixedOutflowTotal),
                            accent: AppColors.coral,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _ReserveMetric(
                            label: 'Apartar por quincena',
                            value: formatCurrency(controller.reservePerQuincena),
                            accent: AppColors.petrol,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    ...controller.quincenaReserveViews.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Row(
                          children: [
                            Container(
                              width: 10,
                              height: 10,
                              decoration: BoxDecoration(
                                color: item.label.contains('Primera')
                                    ? AppColors.gold
                                    : item.label.contains('Segunda')
                                        ? AppColors.sky
                                        : AppColors.emerald,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(item.label, style: textTheme.titleMedium),
                                  const SizedBox(height: 2),
                                  Text(item.detail, style: textTheme.bodyMedium),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text(formatCurrency(item.amount), style: textTheme.titleMedium),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Radar de gastos',
                subtitle: 'Comparativa rapida entre este mes y el mes anterior por categoria.',
              ),
              const SizedBox(height: 16),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _ReserveMetric(
                            label: 'Mes actual',
                            value: formatCurrency(controller.currentMonthExpenseTotal),
                            accent: AppColors.petrol,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _ReserveMetric(
                            label: 'Mes previo',
                            value: formatCurrency(controller.previousMonthExpenseTotal),
                            accent: AppColors.gold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    if (expenseComparisons.isEmpty)
                      Text(
                        'Todavia no hay suficientes gastos registrados para dibujar el radar.',
                        style: textTheme.bodyMedium,
                      )
                    else
                      ...expenseComparisons.map(
                        (item) => Padding(
                          padding: const EdgeInsets.only(bottom: 16),
                          child: _CategoryTrendBar(item: item, maxAmount: highestExpense),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Buckets del mes',
                subtitle: 'Lo reservado hoy vs. el objetivo planeado.',
              ),
              const SizedBox(height: 16),
              ...controller.bucketOverviews.map(
                (bucket) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(bucket.label, style: textTheme.titleMedium),
                            ),
                            Text(
                              '${((bucket.reserved / (bucket.total == 0 ? 1 : bucket.total)) * 100).round()}%',
                              style: textTheme.labelLarge,
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(999),
                          child: LinearProgressIndicator(
                            minHeight: 10,
                            value: (bucket.reserved / (bucket.total == 0 ? 1 : bucket.total)).clamp(0, 1),
                            backgroundColor: AppColors.sand,
                            valueColor: AlwaysStoppedAnimation(AppColors.emerald),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          '${formatCurrency(bucket.reserved)} de ${formatCurrency(bucket.total)}',
                          style: textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Carteras',
                subtitle: 'Liquidez actual por origen del dinero.',
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: controller.walletBalances
                    .map(
                      (wallet) => Chip(
                        avatar: const Icon(Icons.account_balance_wallet_outlined, size: 18),
                        label: Text('${wallet.label} · ${formatCurrency(wallet.amount)}'),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Alertas y oportunidades',
                subtitle: 'Insights explicables, no cajas negras.',
              ),
              const SizedBox(height: 16),
              ...controller.generatedInsights.map(
                (insight) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(insight.title, style: textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(insight.body, style: textTheme.bodyMedium),
                      ],
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
}

class _HeroStat extends StatelessWidget {
  const _HeroStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.white70)),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white)),
        ],
      ),
    );
  }
}

class _ReserveMetric extends StatelessWidget {
  const _ReserveMetric({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 18,
            height: 4,
            decoration: BoxDecoration(
              color: accent,
              borderRadius: BorderRadius.circular(999),
            ),
          ),
          const SizedBox(height: 10),
          Text(label, style: textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(value, style: textTheme.titleMedium),
        ],
      ),
    );
  }
}

class _CategoryTrendBar extends StatelessWidget {
  const _CategoryTrendBar({required this.item, required this.maxAmount});

  final CategorySpendComparison item;
  final double maxAmount;

  @override
  Widget build(BuildContext context) {
    final accent = AppVisuals.colorFromToken(item.colorToken);
    final textTheme = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(AppVisuals.iconFromToken(item.iconToken), color: accent, size: 18),
            ),
            const SizedBox(width: 12),
            Expanded(child: Text(item.label, style: textTheme.titleMedium)),
            const SizedBox(width: 12),
            Text(formatCurrency(item.currentAmount), style: textTheme.titleMedium),
          ],
        ),
        const SizedBox(height: 10),
        _TrendLane(
          label: 'Mes actual',
          amount: item.currentAmount,
          maxAmount: maxAmount,
          color: accent,
        ),
        const SizedBox(height: 8),
        _TrendLane(
          label: 'Mes previo',
          amount: item.previousAmount,
          maxAmount: maxAmount,
          color: AppColors.sand,
          textColor: AppColors.slate,
        ),
      ],
    );
  }
}

class _TrendLane extends StatelessWidget {
  const _TrendLane({
    required this.label,
    required this.amount,
    required this.maxAmount,
    required this.color,
    this.textColor,
  });

  final String label;
  final double amount;
  final double maxAmount;
  final Color color;
  final Color? textColor;

  @override
  Widget build(BuildContext context) {
    final ratio = maxAmount == 0 ? 0.0 : (amount / maxAmount).clamp(0, 1).toDouble();

    return Row(
      children: [
        SizedBox(
          width: 70,
          child: Text(label, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: textColor)),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              minHeight: 10,
              value: ratio,
              backgroundColor: AppColors.ivory,
              valueColor: AlwaysStoppedAnimation(color),
            ),
          ),
        ),
        const SizedBox(width: 10),
        SizedBox(
          width: 74,
          child: Text(
            formatCurrency(amount),
            textAlign: TextAlign.right,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: textColor),
          ),
        ),
      ],
    );
  }
}