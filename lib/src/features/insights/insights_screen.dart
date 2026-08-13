import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/ui/app_card.dart';
import '../../core/ui/section_header.dart';
import '../../state/app_controller.dart';

class InsightsScreen extends StatelessWidget {
  const InsightsScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final textTheme = Theme.of(context).textTheme;
        final bucketOverviews = controller.bucketOverviews;

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Insights', style: textTheme.displaySmall),
              const SizedBox(height: 8),
              Text(
                'Sugerencias locales, auditables y pensadas para ingresos variables.',
                style: textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Estado del mes', style: textTheme.titleMedium),
                    const SizedBox(height: 14),
                    _HealthRow(
                      label: 'Necesidades y fijos',
                      progress: controller.quincenaCoverage,
                    ),
                    _HealthRow(
                      label: 'Uso personal',
                      progress: ((bucketOverviews[1].reserved / (bucketOverviews[1].total == 0 ? 1 : bucketOverviews[1].total)).clamp(0, 1)),
                    ),
                    _HealthRow(
                      label: 'Ahorro e inversion',
                      progress: ((bucketOverviews[2].reserved / (bucketOverviews[2].total == 0 ? 1 : bucketOverviews[2].total)).clamp(0, 1)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              const SectionHeader(
                title: 'Recomendaciones',
                subtitle: 'Cada insight debe explicar el por que del ajuste sugerido.',
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
              const SizedBox(height: 16),
              AppCard(
                backgroundColor: const Color(0xFFF2F7F2),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Criterio actual del motor', style: textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text(
                      'La regla 50, 30, 20 se usa como objetivo adaptable. El disponible personal visible se calcula sobre el ingreso acumulado del mes y baja cuando registras gastos personales.',
                      style: textTheme.bodyMedium,
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

class _HealthRow extends StatelessWidget {
  const _HealthRow({required this.label, required this.progress});

  final String label;
  final double progress;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(label, style: textTheme.bodyMedium)),
              Text('${(progress * 100).round()}%', style: textTheme.titleMedium),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              minHeight: 10,
              value: progress,
              backgroundColor: AppColors.sand,
              valueColor: AlwaysStoppedAnimation(AppColors.gold),
            ),
          ),
        ],
      ),
    );
  }
}