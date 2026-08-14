from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .defaults import DEFAULT_WALLETS
from .schemas import AllocationSuggestion, BootstrapResponse, BucketOverview, CategoryConfig, CategorySpendComparison, CreditCard, CreditCardAlert, CreditCardStatement, DashboardSummary, FixedIncomeSource, InsightView, Obligation, QuincenaReserveView, TagConfig, Transaction, UserRole, WalletBalanceView


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


def _payments_per_month(cadence: str) -> int:
    if cadence == 'weekly':
        return 4
    if cadence == 'biweekly':
        return 2
    return 1


def _monthly_expected_amount(amount: float, cadence: str) -> float:
    return amount * _payments_per_month(cadence)


def _statement_personal_totals_by_transaction(statements: list[CreditCardStatement], transactions: list[Transaction]) -> dict[int, float]:
    statements_by_id = {item.id: item for item in statements}
    payments_by_statement: dict[int, list[Transaction]] = {}
    for transaction in sorted(transactions, key=lambda item: (item.date, item.id)):
        if transaction.credit_card_statement_id is None:
            continue
        payments_by_statement.setdefault(transaction.credit_card_statement_id, []).append(transaction)

    personal_by_transaction: dict[int, float] = {}
    for statement_id, payments in payments_by_statement.items():
        statement = statements_by_id.get(statement_id)
        if statement is None:
            continue
        remaining_fixed_total = statement.fixed_items_total
        for payment in payments:
            fixed_portion = min(payment.amount, max(remaining_fixed_total, 0))
            remaining_fixed_total = max(remaining_fixed_total - fixed_portion, 0)
            personal_by_transaction[payment.id] = max(payment.amount - fixed_portion, 0)
    return personal_by_transaction


def _credit_card_alerts(statements: list[CreditCardStatement]) -> list[CreditCardAlert]:
    today = datetime.now().date()
    alerts: list[CreditCardAlert] = []
    for statement in statements:
        if statement.remaining_amount <= 0:
            continue
        days_until_due = (statement.due_date - today).days
        if days_until_due > 5:
            continue
        severity = 'danger' if days_until_due < 0 else 'warning' if days_until_due <= 2 else 'calm'
        detail = f'Quedan {statement.remaining_amount:.0f} por pagar antes del {statement.due_date.isoformat()}.' if days_until_due >= 0 else f'La fecha limite fue {statement.due_date.isoformat()} y aun quedan {statement.remaining_amount:.0f} pendientes.'
        alerts.append(CreditCardAlert(statement_id=statement.id, credit_card_id=statement.credit_card_id, card_label=statement.card_label, card_last4=statement.card_last4, title=f'TC {statement.card_last4} en seguimiento', detail=detail, severity=severity, days_until_due=days_until_due, remaining_amount=_round(statement.remaining_amount)))
    return alerts


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


def build_dashboard(fixed_income_sources: list[FixedIncomeSource], obligations: list[Obligation], credit_cards: list[CreditCard], credit_card_statements: list[CreditCardStatement], transactions: list[Transaction], categories: list[CategoryConfig]) -> DashboardSummary:
    now = datetime.now()
    del credit_cards
    transactions_by_id = {item.id: item for item in transactions}
    fixed_income_expected = sum(_monthly_expected_amount(item.amount, item.cadence) for item in fixed_income_sources if item.active)
    income_reported_this_month = sum(item.amount for item in transactions if _is_income(item.kind) and item.date.year == now.year and item.date.month == now.month)
    pending_obligations_total = sum(item.current_period_balance for item in obligations)
    obligations_target = sum(item.current_period_expected_amount for item in obligations)
    obligations_reserved = sum(item.current_period_recorded_amount for item in obligations)
    goals_target = fixed_income_expected * 0.20
    goals_reserved = sum(item.amount for item in transactions if item.kind in {'ahorro', 'inversion', 'deuda'})
    personal_target = fixed_income_expected * 0.30
    personal_from_card_payments = _statement_personal_totals_by_transaction(credit_card_statements, transactions)
    direct_personal_spent = sum(item.amount for item in transactions if item.kind == 'gasto' and item.obligation_id is None and item.credit_card_statement_id is None and item.date.year == now.year and item.date.month == now.month)
    personal_spent_this_month = direct_personal_spent + sum(amount for transaction_id, amount in personal_from_card_payments.items() if (transactions_by_id.get(transaction_id) and transactions_by_id[transaction_id].date.year == now.year and transactions_by_id[transaction_id].date.month == now.month))
    total_expenses_this_month = sum(item.amount for item in transactions if _affects_cash_negatively(item.kind) and item.date.year == now.year and item.date.month == now.month)
    snapshot = FinancialSnapshot(fixed_income_expected=fixed_income_expected, income_reported=income_reported_this_month, pending_obligations=pending_obligations_total)
    latest_income_amount = next((item.amount for item in transactions if _is_income(item.kind)), 0)
    latest_income_suggestion = suggest_income_allocation(latest_income_amount, snapshot)
    recommended_personal_budget_this_month = suggest_income_allocation(income_reported_this_month, snapshot).for_personal
    remaining_personal_recommended_this_month = max(recommended_personal_budget_this_month - personal_spent_this_month, 0)
    income_gap = max(fixed_income_expected - income_reported_this_month, 0)
    free_margin_target = max(fixed_income_expected - obligations_target - goals_target - personal_target, 0)
    free_margin_available_now = max(income_reported_this_month - obligations_target - goals_target - personal_target, 0)
    quincena_coverage = 1 if obligations_target == 0 else max(0, min(obligations_reserved / obligations_target, 1))
    current_month_expense_total = sum(item.amount for item in transactions if item.kind == 'gasto' and item.date.year == now.year and item.date.month == now.month)
    previous_month_expense_total = sum(item.amount for item in transactions if item.kind == 'gasto' and item.date.year == datetime(now.year, now.month - 1, 1).year and item.date.month == datetime(now.year, now.month - 1, 1).month)
    monthly_fixed_outflow_total = sum(_monthly_expected_amount(item.amount, item.cadence) for item in obligations)
    reserve_per_quincena = monthly_fixed_outflow_total / 2

    def first_half(item: Obligation) -> float:
        if item.cadence == 'monthly':
            return item.amount if item.due_day <= 15 else 0
        if item.cadence == 'biweekly':
            return item.amount
        return item.amount * 2

    def second_half(item: Obligation) -> float:
        if item.cadence == 'monthly':
            return item.amount if item.due_day > 15 else 0
        if item.cadence == 'biweekly':
            return item.amount
        return item.amount * 2

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
    credit_card_alerts = _credit_card_alerts(credit_card_statements)
    delivery_expenses = sum(item.amount for item in transactions if item.category == 'Delivery')
    if delivery_expenses > 2500:
        insights.append(InsightView(title='Delivery por encima de tendencia', body='Tus gastos en delivery ya superan el umbral mensual esperado. Conviene recortar antes de abrir mas presupuesto personal.'))
    if income_reported_this_month >= fixed_income_expected:
        insights.append(InsightView(title='Capacidad de ahorro al alza', body='Ya alcanzaste o superaste el minimo esperado del mes; puedes desviar una mayor parte del siguiente ingreso a ahorro o inversion.'))
    else:
        insights.append(InsightView(title='Ingreso base aun incompleto', body=f'Todavia faltan {_round(income_gap):.0f} para llegar al ingreso fijo esperado. El motor debe ser conservador con gasto personal.'))
    insights.append(InsightView(title='Disponible personal real', body=f'Con los ingresos ya registrados, te quedan {_round(remaining_personal_recommended_this_month):.0f} dentro de la recomendacion personal del mes.'))
    if credit_card_alerts:
        insights.append(InsightView(title='Tarjetas con fecha cercana', body=f'Tienes {len(credit_card_alerts)} estado(s) de cuenta que requieren seguimiento esta semana.'))

    return DashboardSummary(
        safe_personal_available=_round(remaining_personal_recommended_this_month),
        fixed_income_expected=_round(fixed_income_expected),
        income_reported_this_month=_round(income_reported_this_month),
        free_margin_target=_round(free_margin_target),
        free_margin_available_now=_round(free_margin_available_now),
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
            BucketOverview(label='Personal', reserved=_round(personal_spent_this_month), total=_round(fixed_income_expected * 0.30)),
            BucketOverview(label='Ahorro, inversion y deuda', reserved=_round(goals_reserved), total=_round(goals_target)),
        ],
        expense_comparisons=[CategorySpendComparison(label=label, color_token=category_by_label.get(label).color_token if label in category_by_label else 'gold', icon_token=category_by_label.get(label).icon_token if label in category_by_label else 'receipt', current_amount=_round(current_category_totals.get(label, 0)), previous_amount=_round(previous_category_totals.get(label, 0))) for label in labels[:5]],
        credit_card_alerts=credit_card_alerts,
        generated_insights=insights,
    )


def build_bootstrap(fixed_income_sources: list[FixedIncomeSource], obligations: list[Obligation], credit_cards: list[CreditCard], credit_card_statements: list[CreditCardStatement], transactions: list[Transaction], categories: list[CategoryConfig], tags: list[TagConfig]) -> BootstrapResponse:
    return BootstrapResponse(setup_complete=False, theme_id='emerald_editorial', current_username='', current_user_role=UserRole.operator, can_manage_users=False, can_edit_data=True, users=[], audit_events=[], fixed_income_sources=fixed_income_sources, obligations=obligations, credit_cards=credit_cards, credit_card_statements=credit_card_statements, transactions=transactions, categories=categories, tags=tags, wallets=DEFAULT_WALLETS, dashboard=build_dashboard(fixed_income_sources, obligations, credit_cards, credit_card_statements, transactions, categories))