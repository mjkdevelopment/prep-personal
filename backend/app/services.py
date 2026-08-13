from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .defaults import DEFAULT_WALLETS
from .schemas import AllocationSuggestion, BootstrapResponse, BucketOverview, CategoryConfig, CategorySpendComparison, DashboardSummary, FixedIncomeSource, InsightView, Obligation, QuincenaReserveView, TagConfig, Transaction, UserRole, WalletBalanceView


@dataclass
class FinancialSnapshot:
    fixed_income_expected: float
    income_reported: float
    pending_obligations: float


def _round(value: float) -> float:
    return round(value + 1e-9, 2)


def _is_income(kind: str) -> bool:
    return kind == 'ingreso'


def _affects_cash_negatively(kind: str) -> bool:
    return kind in {'gasto', 'ahorro', 'inversion', 'deuda'}


def suggest_income_allocation(amount: float, snapshot: FinancialSnapshot) -> AllocationSuggestion:
    if amount <= 0:
        return AllocationSuggestion(for_obligations=0, for_goals=0, for_personal=0, rationale='Introduce un monto valido para generar una recomendacion.')

    income_gap = max(snapshot.fixed_income_expected - snapshot.income_reported, 0)
    needs_pressure = snapshot.pending_obligations > 0 or income_gap > 0
    personal_ratio = 0.18 if needs_pressure else 0.30
    goals_ratio = 0.24 if snapshot.income_reported >= snapshot.fixed_income_expected else 0.16
    obligations_allocation = min(_round(amount * 0.55 if amount < snapshot.pending_obligations else snapshot.pending_obligations), amount)
    after_obligations = amount - obligations_allocation
    goals_allocation = min(_round(after_obligations * goals_ratio), after_obligations)
    after_goals = after_obligations - goals_allocation
    personal_allocation = min(_round(after_goals if after_goals < amount * personal_ratio else amount * personal_ratio), after_goals)
    leftover = amount - obligations_allocation - goals_allocation - personal_allocation
    adjusted_goals = _round(goals_allocation + leftover)
    rationale = 'Este ingreso debe proteger primero obligaciones y el minimo esperado del mes antes de liberar gasto personal.' if needs_pressure else 'Tus compromisos base estan mas cubiertos; puedes liberar una mayor parte a uso personal sin romper la quincena.'
    return AllocationSuggestion(for_obligations=_round(obligations_allocation), for_goals=adjusted_goals, for_personal=_round(personal_allocation), rationale=rationale)


def build_dashboard(fixed_income_sources: list[FixedIncomeSource], obligations: list[Obligation], transactions: list[Transaction], categories: list[CategoryConfig]) -> DashboardSummary:
    now = datetime.now()
    fixed_income_expected = sum(item.amount for item in fixed_income_sources if item.active)
    income_reported_this_month = sum(item.amount for item in transactions if _is_income(item.kind) and item.date.year == now.year and item.date.month == now.month)
    pending_obligations_total = sum(item.amount for item in obligations if item.status != 'Cubierto')
    obligations_target = sum(item.amount for item in obligations)
    obligations_reserved = sum(item.amount for item in obligations if item.status in {'Cubierto', 'Parcial'})
    goals_target = fixed_income_expected * 0.20
    goals_reserved = sum(item.amount for item in transactions if item.kind in {'ahorro', 'inversion', 'deuda'})
    personal_spent_this_month = sum(item.amount for item in transactions if item.kind == 'gasto' and item.date.year == now.year and item.date.month == now.month)
    total_expenses_this_month = sum(item.amount for item in transactions if _affects_cash_negatively(item.kind) and item.date.year == now.year and item.date.month == now.month)
    snapshot = FinancialSnapshot(fixed_income_expected=fixed_income_expected, income_reported=income_reported_this_month, pending_obligations=pending_obligations_total)
    latest_income_amount = next((item.amount for item in transactions if _is_income(item.kind)), 0)
    latest_income_suggestion = suggest_income_allocation(latest_income_amount, snapshot)
    recommended_personal_budget_this_month = suggest_income_allocation(income_reported_this_month, snapshot).for_personal
    remaining_personal_recommended_this_month = max(recommended_personal_budget_this_month - personal_spent_this_month, 0)
    income_gap = max(fixed_income_expected - income_reported_this_month, 0)
    quincena_coverage = 1 if obligations_target == 0 else max(0, min(obligations_reserved / obligations_target, 1))
    current_month_expense_total = sum(item.amount for item in transactions if item.kind == 'gasto' and item.date.year == now.year and item.date.month == now.month)
    previous_month_expense_total = sum(item.amount for item in transactions if item.kind == 'gasto' and item.date.year == datetime(now.year, now.month - 1, 1).year and item.date.month == datetime(now.year, now.month - 1, 1).month)
    monthly_fixed_outflow_total = sum(item.amount for item in obligations)
    reserve_per_quincena = monthly_fixed_outflow_total / 2

    def first_half(item: Obligation) -> float:
        if item.cadence == 'monthly':
            return item.amount if item.due_day <= 15 else 0
        return item.amount / 2

    def second_half(item: Obligation) -> float:
        if item.cadence == 'monthly':
            return item.amount if item.due_day > 15 else 0
        return item.amount / 2

    category_by_label = {item.label: item for item in categories}
    current_category_totals: dict[str, float] = {}
    previous_category_totals: dict[str, float] = {}
    prev_month = datetime(now.year, now.month - 1, 1)
    for transaction in transactions:
        if transaction.kind != 'gasto':
            continue
        if transaction.date.year == now.year and transaction.date.month == now.month:
            current_category_totals[transaction.category] = current_category_totals.get(transaction.category, 0) + transaction.amount
        if transaction.date.year == prev_month.year and transaction.date.month == prev_month.month:
            previous_category_totals[transaction.category] = previous_category_totals.get(transaction.category, 0) + transaction.amount

    labels = sorted(set(current_category_totals) | set(previous_category_totals), key=lambda label: current_category_totals.get(label, 0) + previous_category_totals.get(label, 0), reverse=True)

    insights = []
    delivery_expenses = sum(item.amount for item in transactions if item.category == 'Delivery')
    if delivery_expenses > 2500:
        insights.append(InsightView(title='Delivery por encima de tendencia', body='Tus gastos en delivery ya superan el umbral mensual esperado. Conviene recortar antes de abrir mas presupuesto personal.'))
    if income_reported_this_month >= fixed_income_expected:
        insights.append(InsightView(title='Capacidad de ahorro al alza', body='Ya alcanzaste o superaste el minimo esperado del mes; puedes desviar una mayor parte del siguiente ingreso a ahorro o inversion.'))
    else:
        insights.append(InsightView(title='Ingreso base aun incompleto', body=f'Todavia faltan {_round(income_gap):.0f} para llegar al ingreso fijo esperado. El motor debe ser conservador con gasto personal.'))
    insights.append(InsightView(title='Disponible personal real', body=f'Con los ingresos ya registrados, te quedan {_round(remaining_personal_recommended_this_month):.0f} dentro de la recomendacion personal del mes.'))

    return DashboardSummary(
        safe_personal_available=_round(remaining_personal_recommended_this_month),
        fixed_income_expected=_round(fixed_income_expected),
        income_reported_this_month=_round(income_reported_this_month),
        current_month_expense_total=_round(current_month_expense_total),
        previous_month_expense_total=_round(previous_month_expense_total),
        monthly_fixed_outflow_total=_round(monthly_fixed_outflow_total),
        reserve_per_quincena=_round(reserve_per_quincena),
        pending_obligations_total=_round(pending_obligations_total),
        obligations_target=_round(obligations_target),
        obligations_reserved=_round(obligations_reserved),
        goals_target=_round(goals_target),
        goals_reserved=_round(goals_reserved),
        personal_spent_this_month=_round(personal_spent_this_month),
        recommended_personal_budget_this_month=_round(recommended_personal_budget_this_month),
        remaining_personal_recommended_this_month=_round(remaining_personal_recommended_this_month),
        income_gap=_round(income_gap),
        quincena_coverage=quincena_coverage,
        latest_income_amount=_round(latest_income_amount),
        latest_income_suggestion=latest_income_suggestion,
        quincena_reserve_views=[
            QuincenaReserveView(label='Apartado por quincena', amount=_round(reserve_per_quincena), detail='Meta base si quieres repartir el mes en dos bloques iguales.'),
            QuincenaReserveView(label='Primera quincena', amount=_round(sum(first_half(item) for item in obligations)), detail='Compromisos con vencimiento del dia 1 al 15.'),
            QuincenaReserveView(label='Segunda quincena', amount=_round(sum(second_half(item) for item in obligations)), detail='Compromisos con vencimiento del dia 16 al cierre del mes.'),
        ],
        wallet_balances=[WalletBalanceView(label=wallet, amount=_round(sum(item.amount if _is_income(item.kind) else (-item.amount if _affects_cash_negatively(item.kind) else 0) for item in transactions if item.wallet == wallet))) for wallet in DEFAULT_WALLETS],
        bucket_overviews=[
            BucketOverview(label='Obligaciones fijas', reserved=_round(obligations_reserved), total=_round(obligations_target)),
            BucketOverview(label='Personal', reserved=_round(max(total_expenses_this_month - goals_reserved, 0)), total=_round(fixed_income_expected * 0.30)),
            BucketOverview(label='Ahorro, inversion y deuda', reserved=_round(goals_reserved), total=_round(goals_target)),
        ],
        expense_comparisons=[CategorySpendComparison(label=label, color_token=category_by_label.get(label).color_token if label in category_by_label else 'gold', icon_token=category_by_label.get(label).icon_token if label in category_by_label else 'receipt', current_amount=_round(current_category_totals.get(label, 0)), previous_amount=_round(previous_category_totals.get(label, 0))) for label in labels[:5]],
        generated_insights=insights,
    )


def build_bootstrap(fixed_income_sources: list[FixedIncomeSource], obligations: list[Obligation], transactions: list[Transaction], categories: list[CategoryConfig], tags: list[TagConfig]) -> BootstrapResponse:
    return BootstrapResponse(setup_complete=False, theme_id='emerald_editorial', current_username='', current_user_role=UserRole.operator, can_manage_users=False, can_edit_data=True, users=[], audit_events=[], fixed_income_sources=fixed_income_sources, obligations=obligations, transactions=transactions, categories=categories, tags=tags, wallets=DEFAULT_WALLETS, dashboard=build_dashboard(fixed_income_sources, obligations, transactions, categories))