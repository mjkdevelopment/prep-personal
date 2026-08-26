from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .defaults import DEFAULT_WALLETS
from .schemas import AllocationSuggestion, BootstrapResponse, BucketOverview, CategoryConfig, CategorySpendComparison, CreditCard, CreditCardAlert, CreditCardStatement, DashboardSummary, Debt, FixedIncomeSource, InsightView, MonthCloseSnapshot, Obligation, QuincenaReserveView, RestrictedAsset, TagConfig, Transaction, UserRole, WalletBalanceView


@dataclass
class FinancialSnapshot:
    fixed_income_expected: float
    income_reported: float
    pending_obligations: float
    overdue_obligations: float = 0
    debt_payment_target: float = 0
    debt_total_balance: float = 0
    has_extra_payment_debt: bool = False


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


def _wallet_balance_views(fixed_income_sources: list[FixedIncomeSource], transactions: list[Transaction]) -> list[WalletBalanceView]:
    now = datetime.now()
    active_wallets = {
        item.wallet for item in fixed_income_sources if item.active
    } | {
        item.wallet for item in transactions if item.wallet
    } | set(DEFAULT_WALLETS)
    wallet_views: list[WalletBalanceView] = []
    for wallet in sorted(active_wallets, key=lambda item: DEFAULT_WALLETS.index(item) if item in DEFAULT_WALLETS else len(DEFAULT_WALLETS)):
        expected_income_amount = sum(_monthly_expected_amount(item.amount, item.cadence) for item in fixed_income_sources if item.active and item.wallet == wallet)
        reported_income_amount = sum(item.amount for item in transactions if item.wallet == wallet and _is_income(item.kind) and item.date.year == now.year and item.date.month == now.month)
        amount = sum(item.amount if _is_income(item.kind) else (-item.amount if _affects_cash_negatively(item.kind) else 0) for item in transactions if item.wallet == wallet)
        pending_income_amount = max(expected_income_amount - reported_income_amount, 0)
        wallet_views.append(
            WalletBalanceView(
                label=wallet,
                amount=_round(amount),
                expected_income_amount=_round(expected_income_amount),
                reported_income_amount=_round(reported_income_amount),
                pending_income_amount=_round(pending_income_amount),
            )
        )
    return wallet_views


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


def _annualized_interest_rate_percent(debt: Debt) -> float:
    if debt.interest_rate_percent is None:
        return 0.0
    if debt.interest_rate_period == 'monthly':
        return debt.interest_rate_percent * 12
    return debt.interest_rate_percent


def _debt_balance_update_stale(debt: Debt, reference: datetime | None = None) -> bool:
    if not debt.last_balance_reported_at_iso:
        return True
    base = reference or datetime.now()
    try:
        last_reported = datetime.fromisoformat(debt.last_balance_reported_at_iso)
    except ValueError:
        return True
    return (base - last_reported).days > 45


def _debt_priority_snapshot(debts: list[Debt]) -> tuple[str, str, int]:
    active_debts = [item for item in debts if item.active and item.balance_amount > 0]
    if not active_debts:
        return '', 'No hay deuda activa con saldo pendiente.', 0

    stale_count = sum(1 for item in active_debts if item.balance_update_stale)
    ranked = sorted(
        active_debts,
        key=lambda item: (
            0 if item.allow_extra_payment else 1,
            -_annualized_interest_rate_percent(item),
            -item.monthly_payment_amount,
            -item.balance_amount,
        ),
    )
    target = ranked[0]
    annual_rate = _annualized_interest_rate_percent(target)
    if annual_rate > 0:
        reason = f'{target.label} deberia mirarse primero por su tasa anual equivalente de {annual_rate:.2f}% y saldo confirmado de {_round(target.balance_amount):.0f}.'
    elif target.amortization_mode == 'fixed_principal' and target.fixed_principal_payment_amount:
        reason = f'{target.label} usa capital fijo de {_round(target.fixed_principal_payment_amount):.0f} por cuota. Sirve como estimacion operativa hasta que registres el saldo oficial.'
    elif target.allow_extra_payment:
        reason = f'{target.label} deberia mirarse primero porque permite abonos extra y mantiene un saldo confirmado de {_round(target.balance_amount):.0f}.'
    else:
        reason = f'{target.label} deberia vigilarse primero por su peso mensual de {_round(target.monthly_payment_amount):.0f}, aunque no tenga tasa registrada.'
    return target.label, reason, stale_count


def _enriched_debts(debts: list[Debt]) -> list[Debt]:
    staged = [Debt(**{**item.model_dump(), 'balance_update_stale': _debt_balance_update_stale(item)}) for item in debts]
    priority_label, priority_reason, _ = _debt_priority_snapshot(staged)
    enriched: list[Debt] = []
    for item in staged:
        item_reason = priority_reason if item.label == priority_label else (f'Registra tasa para priorizar mejor {item.label}.' if item.interest_rate_percent is None else '')
        enriched.append(Debt(**{**item.model_dump(), 'priority_reason': item_reason, 'priority_score': _annualized_interest_rate_percent(item)}))
    return enriched


def suggest_income_allocation(amount: float, snapshot: FinancialSnapshot) -> AllocationSuggestion:
    if amount <= 0:
        return AllocationSuggestion(for_obligations=0, for_goals=0, for_personal=0, rationale='Introduce un monto valido para generar una recomendacion.')

    personal_allocation = _round(amount * 0.30)
    capitalization_floor = _round(amount * 0.20)
    fixed_ceiling = _round(max(amount - personal_allocation - capitalization_floor, 0))
    obligations_need = max(snapshot.pending_obligations, snapshot.overdue_obligations)
    obligations_allocation = min(fixed_ceiling, obligations_need, amount - personal_allocation)
    goals_allocation = _round(max(amount - personal_allocation - obligations_allocation, 0))
    if snapshot.overdue_obligations > 0:
        rationale = 'El 30% personal se mantiene, pero la capitalizacion restante debe ponerse primero al dia con atrasos y deuda prioritaria.'
    elif snapshot.debt_total_balance > 0:
        rationale = 'Tu 30% personal queda blindado; el resto que no necesiten los fijos debe capitalizarse y dirigirse primero a deuda.'
    elif snapshot.pending_obligations > 0:
        rationale = 'Tu 30% personal queda blindado; cubre los fijos reales sin pasar de 50% y capitaliza el sobrante restante.'
    else:
        rationale = 'Tu 30% personal queda blindado y la capitalizacion puede fortalecer primero fondo de seguridad y luego inversion.'
    return AllocationSuggestion(for_obligations=_round(obligations_allocation), for_goals=_round(goals_allocation), for_personal=_round(personal_allocation), rationale=rationale)


def build_dashboard(fixed_income_sources: list[FixedIncomeSource], obligations: list[Obligation], debts: list[Debt], restricted_assets: list[RestrictedAsset], credit_cards: list[CreditCard], credit_card_statements: list[CreditCardStatement], transactions: list[Transaction], categories: list[CategoryConfig], emergency_fund_months: int = 3) -> DashboardSummary:
    now = datetime.now()
    del credit_cards
    transactions_by_id = {item.id: item for item in transactions}
    debts = _enriched_debts(debts)
    fixed_income_expected = sum(_monthly_expected_amount(item.amount, item.cadence) for item in fixed_income_sources if item.active)
    income_reported_this_month = sum(item.amount for item in transactions if _is_income(item.kind) and item.date.year == now.year and item.date.month == now.month)
    pending_obligations_total = sum(item.current_period_balance for item in obligations)
    overdue_obligations_total = sum(item.current_period_balance for item in obligations if item.current_period_balance > 0 and item.cadence == 'monthly' and item.due_day < now.day)
    obligations_target = sum(item.current_period_expected_amount for item in obligations)
    obligations_reserved = sum(item.current_period_recorded_amount for item in obligations)
    active_debts = [item for item in debts if item.active]
    debt_payment_target = sum(item.monthly_payment_amount for item in active_debts)
    debt_total_balance = sum(item.balance_amount for item in active_debts)
    restricted_assets_total = sum(item.balance_amount for item in restricted_assets if item.active and item.availability_status == 'restricted')
    available_restricted_assets_total = sum(item.balance_amount for item in restricted_assets if item.active and item.availability_status == 'available')
    has_extra_payment_debt = any(item.allow_extra_payment and item.balance_amount > 0 for item in active_debts)
    debt_priority_label, debt_priority_reason, stale_debt_update_count = _debt_priority_snapshot(active_debts)
    monthly_fixed_outflow_total = sum(_monthly_expected_amount(item.amount, item.cadence) for item in obligations)
    personal_target = income_reported_this_month * 0.30
    goals_reserved = sum(item.amount for item in transactions if item.kind in {'ahorro', 'inversion', 'deuda'} and item.date.year == now.year and item.date.month == now.month)
    lifetime_savings_balance = max(sum(item.amount for item in transactions if item.kind == 'ahorro') - sum(item.amount for item in transactions if item.kind == 'inversion'), 0)
    fixed_cost_ceiling = income_reported_this_month * 0.50
    fixed_cost_headroom = max(fixed_cost_ceiling - obligations_target, 0)
    fixed_cost_overflow = max(obligations_target - fixed_cost_ceiling, 0)
    goals_target = (income_reported_this_month * 0.20) + fixed_cost_headroom
    capitalization_gap = max(goals_target - goals_reserved, 0)
    emergency_fund_target = monthly_fixed_outflow_total * (emergency_fund_months if emergency_fund_months in {3, 6} else 3)
    emergency_fund_current = lifetime_savings_balance
    emergency_fund_gap = max(emergency_fund_target - emergency_fund_current, 0)
    investable_surplus = max(emergency_fund_current - emergency_fund_target, 0)
    investment_limit_amount = investable_surplus * 0.30
    investment_unlocked = debt_total_balance <= 0 and emergency_fund_gap <= 0 and investment_limit_amount > 0
    personal_from_card_payments = _statement_personal_totals_by_transaction(credit_card_statements, transactions)
    direct_personal_spent = sum(item.amount for item in transactions if item.kind == 'gasto' and item.obligation_id is None and item.credit_card_statement_id is None and item.date.year == now.year and item.date.month == now.month)
    personal_spent_this_month = direct_personal_spent + sum(amount for transaction_id, amount in personal_from_card_payments.items() if (transactions_by_id.get(transaction_id) and transactions_by_id[transaction_id].date.year == now.year and transactions_by_id[transaction_id].date.month == now.month))
    total_expenses_this_month = sum(item.amount for item in transactions if _affects_cash_negatively(item.kind) and item.date.year == now.year and item.date.month == now.month)
    debt_extra_payment_capacity = max(capitalization_gap, 0) if has_extra_payment_debt else 0
    snapshot = FinancialSnapshot(fixed_income_expected=fixed_income_expected, income_reported=income_reported_this_month, pending_obligations=pending_obligations_total, overdue_obligations=overdue_obligations_total, debt_payment_target=debt_payment_target, debt_total_balance=debt_total_balance, has_extra_payment_debt=has_extra_payment_debt)
    latest_income_amount = next((item.amount for item in transactions if _is_income(item.kind)), 0)
    latest_income_suggestion = suggest_income_allocation(latest_income_amount, snapshot)
    recommended_personal_budget_this_month = _round(personal_target)
    remaining_personal_recommended_this_month = max(recommended_personal_budget_this_month - personal_spent_this_month, 0)
    income_gap = max(fixed_income_expected - income_reported_this_month, 0)
    expected_fixed_ceiling = fixed_income_expected * 0.50
    expected_fixed_headroom = max(expected_fixed_ceiling - obligations_target, 0)
    free_margin_target = max((fixed_income_expected * 0.20) + expected_fixed_headroom, 0)
    free_margin_available_now = max(goals_target, 0)
    quincena_coverage = 1 if obligations_target == 0 else max(0, min(obligations_reserved / obligations_target, 1))
    current_month_expense_total = sum(item.amount for item in transactions if item.kind == 'gasto' and item.date.year == now.year and item.date.month == now.month)
    previous_month_expense_total = sum(item.amount for item in transactions if item.kind == 'gasto' and item.date.year == datetime(now.year, now.month - 1, 1).year and item.date.month == datetime(now.year, now.month - 1, 1).month)
    reserve_per_quincena = monthly_fixed_outflow_total / 2
    fixed_cost_progress_ratio = 1 if fixed_cost_ceiling <= 0 else max(0, min(obligations_target / fixed_cost_ceiling, 1))

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
    if fixed_cost_overflow > 0:
        insights.append(InsightView(title='Alerta fuerte: fijos por encima de 50%', body=f'Tus gastos fijos necesitan {_round(obligations_target):.0f} este mes y ya exceden el techo sano de {_round(fixed_cost_ceiling):.0f}. Conviene recortar o renegociar antes de abrir nuevas cargas.'))
    elif overdue_obligations_total > 0:
        insights.append(InsightView(title='Arrastre pendiente al cierre actual', body=f'Hay {_round(overdue_obligations_total):.0f} vencidos del mes en curso. Antes de hablar de excedente, conviene normalizar ese arrastre.'))
    if delivery_expenses > 2500:
        insights.append(InsightView(title='Delivery por encima de tendencia', body='Tus gastos en delivery ya superan el umbral mensual esperado. Conviene recortar antes de abrir mas presupuesto personal.'))
    if stale_debt_update_count > 0:
        insights.append(InsightView(title='Deudas con saldo por confirmar', body=f'Tienes {stale_debt_update_count} deuda(s) sin actualizacion reciente. Conviene registrar el balance oficial antes de tomar decisiones agresivas.'))
    if restricted_assets_total > 0:
        insights.append(InsightView(title='Patrimonio restringido', body=f'Tienes {_round(restricted_assets_total):.0f} comprometidos en garantia o restricciones. No se tratan como ingreso disponible.'))
    if available_restricted_assets_total > 0:
        insights.append(InsightView(title='Fondos liberados por mover', body=f'Tienes {_round(available_restricted_assets_total):.0f} ya liberados. Conviene moverlos a una cartera real sin registrarlos como ingreso del mes.'))
    if debt_total_balance > 0:
        insights.append(InsightView(title='Capitalizacion con prioridad deuda', body=f'Con tu politica 50/30/20, la capitalizacion objetivo del mes es {_round(goals_target):.0f} y debe ir primero a deuda hasta sanear el balance actual.'))
        if debt_priority_label:
            insights.append(InsightView(title='Deuda prioritaria sugerida', body=debt_priority_reason))
    elif emergency_fund_gap > 0:
        insights.append(InsightView(title='Fondo de seguridad aun incompleto', body=f'Tu reserva sugerida de {emergency_fund_months if emergency_fund_months in {3, 6} else 3} meses es {_round(emergency_fund_target):.0f}; hoy llevas {_round(emergency_fund_current):.0f}. Antes de invertir conviene cerrar ese faltante.'))
    elif investment_unlocked:
        insights.append(InsightView(title='Inversion habilitada con limite sano', body=f'Ya cubriste deuda y fondo de seguridad. Puedes invertir hasta {_round(investment_limit_amount):.0f} del excedente liquido sin tocar tu base protegida.'))
    if income_reported_this_month < fixed_income_expected:
        insights.append(InsightView(title='Ingreso base aun incompleto', body=f'Todavia faltan {_round(income_gap):.0f} para llegar al ingreso fijo esperado, pero tu 30% personal sigue blindado sobre lo ya cobrado.'))
    insights.append(InsightView(title='Disponible personal blindado', body=f'Con los ingresos ya cobrados, te quedan {_round(remaining_personal_recommended_this_month):.0f} dentro del 30% personal del mes.'))
    insights.append(InsightView(title='Capitalizacion objetivo del mes', body=f'El 20% obligatorio mas el sobrante del techo de fijos te llevan a una meta de {_round(goals_target):.0f} este mes.'))
    if credit_card_alerts:
        insights.append(InsightView(title='Tarjetas con fecha cercana', body=f'Tienes {len(credit_card_alerts)} estado(s) de cuenta que requieren seguimiento esta semana.'))

    if fixed_cost_overflow > 0:
        recommended_free_margin_destination = 'Recortar gastos fijos'
    elif overdue_obligations_total > 0:
        recommended_free_margin_destination = 'Cubrir arrastre vencido'
    elif debt_total_balance > 0 and debt_extra_payment_capacity > 0:
        recommended_free_margin_destination = 'Abonar deuda prioritaria'
    elif emergency_fund_gap > 0:
        recommended_free_margin_destination = 'Construir fondo de seguridad'
    elif goals_reserved < goals_target:
        recommended_free_margin_destination = 'Completar capitalizacion del mes'
    elif investment_unlocked:
        recommended_free_margin_destination = 'Mover una parte a inversion'
    elif pending_obligations_total > 0:
        recommended_free_margin_destination = 'Cerrar obligaciones pendientes'
    else:
        recommended_free_margin_destination = 'Mantener caja conservadora'

    return DashboardSummary(
        safe_personal_available=_round(remaining_personal_recommended_this_month),
        fixed_income_expected=_round(fixed_income_expected),
        income_reported_this_month=_round(income_reported_this_month),
        free_margin_target=_round(free_margin_target),
        free_margin_available_now=_round(free_margin_available_now),
        fixed_cost_ceiling=_round(fixed_cost_ceiling),
        fixed_cost_progress_ratio=fixed_cost_progress_ratio,
        fixed_cost_headroom=_round(fixed_cost_headroom),
        fixed_cost_overflow=_round(fixed_cost_overflow),
        current_month_expense_total=_round(current_month_expense_total),
        previous_month_expense_total=_round(previous_month_expense_total),
        monthly_fixed_outflow_total=_round(monthly_fixed_outflow_total),
        reserve_per_quincena=_round(reserve_per_quincena),
        pending_obligations_total=_round(pending_obligations_total),
        obligations_target=_round(obligations_target),
        obligations_reserved=_round(obligations_reserved),
        overdue_obligations_total=_round(overdue_obligations_total),
        debt_payment_target=_round(debt_payment_target),
        debt_total_balance=_round(debt_total_balance),
        debt_extra_payment_capacity=_round(debt_extra_payment_capacity),
        debt_priority_label=debt_priority_label,
        debt_priority_reason=debt_priority_reason,
        stale_debt_update_count=stale_debt_update_count,
        restricted_assets_total=_round(restricted_assets_total),
        available_restricted_assets_total=_round(available_restricted_assets_total),
        recommended_free_margin_destination=recommended_free_margin_destination,
        goals_target=_round(goals_target),
        goals_reserved=_round(goals_reserved),
        capitalization_target=_round(goals_target),
        capitalization_gap=_round(capitalization_gap),
        emergency_fund_target=_round(emergency_fund_target),
        emergency_fund_current=_round(emergency_fund_current),
        emergency_fund_gap=_round(emergency_fund_gap),
        investable_surplus=_round(investable_surplus),
        investment_limit_amount=_round(investment_limit_amount),
        investment_unlocked=investment_unlocked,
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
        wallet_balances=_wallet_balance_views(fixed_income_sources, transactions),
        bucket_overviews=[
            BucketOverview(label='Gastos fijos', reserved=_round(obligations_reserved), total=_round(obligations_target)),
            BucketOverview(label='Personal blindado', reserved=_round(personal_spent_this_month), total=_round(recommended_personal_budget_this_month)),
            BucketOverview(label='Capitalizacion', reserved=_round(goals_reserved), total=_round(goals_target)),
        ],
        expense_comparisons=[CategorySpendComparison(label=label, color_token=category_by_label.get(label).color_token if label in category_by_label else 'gold', icon_token=category_by_label.get(label).icon_token if label in category_by_label else 'receipt', current_amount=_round(current_category_totals.get(label, 0)), previous_amount=_round(previous_category_totals.get(label, 0))) for label in labels],
        credit_card_alerts=credit_card_alerts,
        generated_insights=insights,
    )


def build_month_close_snapshot(
    fixed_income_sources: list[FixedIncomeSource],
    obligations: list[Obligation],
    debts: list[Debt],
    restricted_assets: list[RestrictedAsset],
    credit_cards: list[CreditCard],
    credit_card_statements: list[CreditCardStatement],
    transactions: list[Transaction],
    categories: list[CategoryConfig],
    emergency_fund_months: int = 3,
) -> dict:
    dashboard = build_dashboard(fixed_income_sources, obligations, debts, restricted_assets, credit_cards, credit_card_statements, transactions, categories, emergency_fund_months)
    active_debts = [item for item in debts if item.active]
    debt_payment_target = _round(sum(item.monthly_payment_amount for item in active_debts))
    debt_total_balance = _round(sum(item.balance_amount for item in active_debts))
    cash_on_hand = _round(sum(item.amount for item in dashboard.wallet_balances))
    income_delta = _round(dashboard.income_reported_this_month - dashboard.fixed_income_expected)
    income_delta_percent = 0.0 if dashboard.fixed_income_expected <= 0 else _round((income_delta / dashboard.fixed_income_expected) * 100)
    goals_shortfall = max(dashboard.goals_target - dashboard.goals_reserved, 0)
    overdue_obligations_amount = dashboard.overdue_obligations_total
    next_cycle_obligations_amount = max(dashboard.pending_obligations_total - overdue_obligations_amount, 0)
    next_cycle_start_buffer = _round(min(max(dashboard.free_margin_available_now - overdue_obligations_amount, 0), next_cycle_obligations_amount + goals_shortfall))
    available_after_buffer = max(dashboard.free_margin_available_now - overdue_obligations_amount - next_cycle_start_buffer, 0)
    suggested_extra_debt_payment = _round(min(available_after_buffer, debt_total_balance)) if any(item.allow_extra_payment for item in active_debts) else 0
    suggested_carryover_amount = _round(overdue_obligations_amount + next_cycle_start_buffer)

    highlights: list[str] = []
    concerns: list[str] = []
    next_actions: list[str] = []

    if income_delta >= 0:
        highlights.append(f'El mes cerro con ingresos por encima de la base en {_round(income_delta):.0f}.')
    else:
        concerns.append(f'El ingreso reportado quedo {_round(abs(income_delta)):.0f} por debajo de la base esperada.')

    if overdue_obligations_amount > 0:
        concerns.append(f'Quedan {_round(overdue_obligations_amount):.0f} vencidos que deben arrastrarse como prioridad al nuevo ciclo.')
        next_actions.append('Liquida primero el arrastre vencido antes de liberar nuevos gastos variables.')
    elif next_cycle_obligations_amount > 0:
        concerns.append(f'Quedan {_round(next_cycle_obligations_amount):.0f} pendientes del ciclo que conviene reservar como arranque del proximo mes.')
        next_actions.append('Separa desde ya el fondo de arranque del siguiente mes antes de decidir excedentes.')
    else:
        highlights.append('Las obligaciones del periodo quedaron cubiertas en el cierre actual.')

    if suggested_extra_debt_payment > 0 and debt_total_balance > 0:
        highlights.append(f'Hay espacio para abonar {_round(suggested_extra_debt_payment):.0f} extra a deuda sin romper la estructura base.')
        next_actions.append('Evalua dirigir el excedente libre a la deuda mas costosa o mas estrategica.')

    if next_cycle_start_buffer > 0:
        highlights.append(f'Conviene arrancar el proximo ciclo con {_round(next_cycle_start_buffer):.0f} ya reservado entre pendientes y ahorro base.')

    if dashboard.remaining_personal_recommended_this_month <= 0:
        concerns.append('El presupuesto personal sugerido ya se consumio por completo en este ciclo.')
        next_actions.append('Arranca el nuevo mes con un tope personal mas vigilado hasta completar los ingresos base.')
    else:
        highlights.append(f'Quedaron {_round(dashboard.remaining_personal_recommended_this_month):.0f} dentro del presupuesto personal sugerido.')

    if not next_actions:
        next_actions.append('Mantiene el mismo criterio de asignacion para el siguiente ingreso y revisa el cierre al final del proximo ciclo.')

    now = datetime.now()
    return {
        'period_year': now.year,
        'period_month': now.month,
        'closed_at_iso': now.isoformat(),
        'income_expected': dashboard.fixed_income_expected,
        'income_reported': dashboard.income_reported_this_month,
        'income_delta': income_delta,
        'income_delta_percent': income_delta_percent,
        'obligations_target': dashboard.obligations_target,
        'obligations_reserved': dashboard.obligations_reserved,
        'pending_obligations': dashboard.pending_obligations_total,
        'cash_on_hand': cash_on_hand,
        'structural_margin': dashboard.free_margin_target,
        'available_margin_now': dashboard.free_margin_available_now,
        'recommended_personal_remaining': dashboard.remaining_personal_recommended_this_month,
        'overdue_obligations_amount': overdue_obligations_amount,
        'next_cycle_obligations_amount': _round(next_cycle_obligations_amount),
        'next_cycle_start_buffer': next_cycle_start_buffer,
        'goals_shortfall_amount': _round(goals_shortfall),
        'debt_payment_target': debt_payment_target,
        'debt_total_balance': debt_total_balance,
        'suggested_carryover_amount': suggested_carryover_amount,
        'suggested_extra_debt_payment': suggested_extra_debt_payment,
        'highlights': highlights,
        'concerns': concerns,
        'next_actions': next_actions,
    }


def build_bootstrap(fixed_income_sources: list[FixedIncomeSource], obligations: list[Obligation], credit_cards: list[CreditCard], credit_card_statements: list[CreditCardStatement], debts: list[Debt], restricted_assets: list[RestrictedAsset], month_close_snapshots: list[MonthCloseSnapshot], transactions: list[Transaction], categories: list[CategoryConfig], tags: list[TagConfig], emergency_fund_months: int = 3) -> BootstrapResponse:
    enriched_debts = _enriched_debts(debts)
    return BootstrapResponse(setup_complete=False, theme_id='emerald_editorial', emergency_fund_months=emergency_fund_months if emergency_fund_months in {3, 6} else 3, current_username='', current_user_role=UserRole.operator, can_manage_users=False, can_edit_data=True, users=[], audit_events=[], fixed_income_sources=fixed_income_sources, obligations=obligations, credit_cards=credit_cards, credit_card_statements=credit_card_statements, debts=enriched_debts, restricted_assets=restricted_assets, month_close_snapshots=month_close_snapshots, transactions=transactions, categories=categories, tags=tags, wallets=DEFAULT_WALLETS, dashboard=build_dashboard(fixed_income_sources, obligations, enriched_debts, restricted_assets, credit_cards, credit_card_statements, transactions, categories, emergency_fund_months))