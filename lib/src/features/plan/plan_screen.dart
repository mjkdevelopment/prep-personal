import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/ui/app_card.dart';
import '../../core/ui/section_header.dart';
import '../../core/utils/formatters.dart';
import '../../domain/models.dart';
import '../../state/app_controller.dart';

class PlanScreen extends StatelessWidget {
  const PlanScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final textTheme = Theme.of(context).textTheme;
        final recommendation = controller.latestIncomeSuggestion;

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Plan de quincena', style: textTheme.displaySmall),
              const SizedBox(height: 8),
              Text(
                'La prioridad del motor es cubrir obligaciones y metas antes de abrir gasto discrecional.',
                style: textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Monto a reservar hoy', style: textTheme.labelLarge),
                    const SizedBox(height: 10),
                    Text(formatCurrency(controller.pendingObligationsTotal), style: textTheme.displaySmall),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: _PlanMetric(
                            label: 'Ingresos registrados',
                            value: formatCurrency(controller.incomeReportedThisMonth),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _PlanMetric(
                            label: 'Cobertura estimada',
                            value: '${(controller.quincenaCoverage * 100).round()}%',
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Apartado por quincena',
                subtitle: 'Referencia rapida para no mirar solo el total mensual de gastos fijos.',
              ),
              const SizedBox(height: 16),
              AppCard(
                backgroundColor: const Color(0xFFFFF8EF),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _PlanMetric(
                            label: 'Total fijo mensual',
                            value: formatCurrency(controller.monthlyFixedOutflowTotal),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _PlanMetric(
                            label: 'Sacar por quincena',
                            value: formatCurrency(controller.reservePerQuincena),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    ...controller.quincenaReserveViews.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(item.label, style: textTheme.titleMedium),
                                  const SizedBox(height: 4),
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
                title: 'Proximas obligaciones',
                subtitle: 'Estado real de cobertura por fecha de vencimiento.',
              ),
              const SizedBox(height: 16),
              ...controller.obligations.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: AppCard(
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(item.label, style: textTheme.titleMedium),
                              const SizedBox(height: 4),
                              Text(item.scheduleLabel, style: textTheme.bodyMedium),
                              const SizedBox(height: 4),
                              Text(
                                switch (item.cadence) {
                                  FixedIncomeCadence.monthly => 'Pago mensual ${formatCurrency(item.installmentExpectedAmount)}',
                                  FixedIncomeCadence.biweekly => '2 pagos de ${formatCurrency(item.installmentExpectedAmount)}',
                                  FixedIncomeCadence.weekly => '4 pagos de ${formatCurrency(item.installmentExpectedAmount)}',
                                },
                                style: textTheme.bodySmall,
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(formatCurrency(item.amount), style: textTheme.titleMedium),
                            const SizedBox(height: 6),
                            _StatusPill(status: item.status),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              AppCard(
                backgroundColor: const Color(0xFFF5F1E9),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Recomendacion inteligente', style: textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text(
                      'Del ultimo ingreso, ${formatCurrency(recommendation.forPersonal)} puede quedar como gasto personal despues de proteger obligaciones y metas.',
                      style: textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 12),
                    _PlanMetric(
                      label: 'Disponible personal acumulado del mes',
                      value: formatCurrency(controller.remainingPersonalRecommendedThisMonth),
                    ),
                    const SizedBox(height: 10),
                    _PlanMetric(
                      label: 'Personal ya usado',
                      value: formatCurrency(controller.personalSpentThisMonth),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Progreso de ingresos', style: textTheme.titleMedium),
                    const SizedBox(height: 12),
                    _PlanMetric(
                      label: 'Ingreso esperado',
                      value: formatCurrency(controller.fixedIncomeExpected),
                    ),
                    const SizedBox(height: 10),
                    _PlanMetric(
                      label: 'Ingreso real acumulado',
                      value: formatCurrency(controller.incomeReportedThisMonth),
                    ),
                    const SizedBox(height: 10),
                    _PlanMetric(
                      label: 'Faltante por cubrir',
                      value: formatCurrency(controller.incomeGap),
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

class _PlanMetric extends StatelessWidget {
  const _PlanMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: textTheme.bodyMedium),
        const SizedBox(height: 6),
        Text(value, style: textTheme.titleMedium),
      ],
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final Color color = switch (status) {
      'Cubierto' => AppColors.success,
      'Parcial' => AppColors.warning,
      _ => AppColors.terracotta,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        status,
        style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 12),
      ),
    );
  }
}