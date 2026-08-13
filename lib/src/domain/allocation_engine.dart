import 'models.dart';

class IncomeAllocationEngine {
  const IncomeAllocationEngine();

  AllocationSuggestion suggest({
    required double amount,
    required FinancialSnapshot snapshot,
  }) {
    if (amount <= 0) {
      return const AllocationSuggestion(
        forObligations: 0,
        forGoals: 0,
        forPersonal: 0,
        rationale: 'Introduce un monto valido para generar una recomendacion.',
      );
    }

    final incomeGap = (snapshot.fixedIncomeExpected - snapshot.incomeReported)
        .clamp(0, double.infinity);
    final needsPressure = snapshot.pendingObligations > 0 || incomeGap > 0;
    final personalRatio = needsPressure ? 0.18 : 0.30;
    final goalsRatio = snapshot.incomeReported >= snapshot.fixedIncomeExpected ? 0.24 : 0.16;

    final obligationsAllocation = (_roundCurrency(
      amount < snapshot.pendingObligations ? amount * 0.55 : snapshot.pendingObligations,
    ).clamp(0, amount))
        .toDouble();

    final afterObligations = amount - obligationsAllocation;
    final goalsAllocation = (_roundCurrency(afterObligations * goalsRatio)
        .clamp(0, afterObligations))
      .toDouble();
    final afterGoals = afterObligations - goalsAllocation;
    final personalAllocation = (_roundCurrency(
      afterGoals < amount * personalRatio ? afterGoals : amount * personalRatio,
    ).clamp(0, afterGoals))
      .toDouble();

    final leftover = amount - obligationsAllocation - goalsAllocation - personalAllocation;
    final adjustedGoals = _roundCurrency(goalsAllocation + leftover);

    final rationale = needsPressure
        ? 'Este ingreso debe proteger primero obligaciones y el minimo esperado del mes antes de liberar gasto personal.'
        : 'Tus compromisos base estan mas cubiertos; puedes liberar una mayor parte a uso personal sin romper la quincena.';

    return AllocationSuggestion(
      forObligations: _roundCurrency(obligationsAllocation),
      forGoals: adjustedGoals,
      forPersonal: _roundCurrency(personalAllocation),
      rationale: rationale,
    );
  }
}

double _roundCurrency(double value) {
  return (value * 100).roundToDouble() / 100;
}