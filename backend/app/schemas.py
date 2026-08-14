from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionKind(str, Enum):
    ingreso = 'ingreso'
    gasto = 'gasto'
    transferencia = 'transferencia'
    ahorro = 'ahorro'
    inversion = 'inversion'
    deuda = 'deuda'


class FixedIncomeCadence(str, Enum):
    monthly = 'monthly'
    biweekly = 'biweekly'
    weekly = 'weekly'


class CategoryScope(str, Enum):
    expense = 'expense'
    income = 'income'


class UserRole(str, Enum):
    owner = 'owner'
    admin = 'admin'
    operator = 'operator'
    viewer = 'viewer'


class FixedIncomeSourceBase(BaseModel):
    label: str = Field(min_length=1)
    amount: float = Field(gt=0)
    cadence: FixedIncomeCadence
    expected_day: int = Field(ge=1, le=31)
    expected_weekday: Optional[int] = Field(default=None, ge=1, le=7)
    wallet: str = Field(min_length=1)
    active: bool = True


class FixedIncomeSourceCreate(FixedIncomeSourceBase):
    pass


class FixedIncomeSource(FixedIncomeSourceBase):
    id: int
    current_period_expected_amount: float = 0
    current_period_recorded_amount: float = 0
    current_period_balance: float = 0


class ObligationBase(BaseModel):
    label: str = Field(min_length=1)
    amount: float = Field(gt=0)
    category_id: Optional[str] = None
    credit_card_id: Optional[int] = None
    cadence: FixedIncomeCadence
    due_day: int = Field(ge=1, le=31)
    due_weekday: Optional[int] = Field(default=None, ge=1, le=7)
    kind: str = Field(min_length=1)
    status: str = Field(min_length=1)


class ObligationCreate(ObligationBase):
    pass


class Obligation(ObligationBase):
    id: int
    current_period_expected_amount: float = 0
    current_period_recorded_amount: float = 0
    current_period_balance: float = 0
    current_period_status: str = 'Pendiente'


class TransactionBase(BaseModel):
    kind: TransactionKind
    amount: float = Field(gt=0)
    wallet: str = Field(min_length=1)
    category: str = Field(min_length=1)
    fixed_income_source_id: Optional[int] = None
    obligation_id: Optional[int] = None
    credit_card_statement_id: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    notes: str = ''
    date: datetime
    recurring: bool = False


class TransactionCreate(TransactionBase):
    pass


class Transaction(TransactionBase):
    id: int


class CategoryConfig(BaseModel):
    id: str
    label: str
    scope: CategoryScope
    type: str
    color_token: str
    icon_token: str
    active: bool = True


class TagConfig(BaseModel):
    id: str
    label: str
    color_token: str
    active: bool = True
    command_enabled: bool = False
    preset_transaction_kind: Optional[TransactionKind] = None
    preset_fixed_income_source_id: Optional[int] = None
    preset_obligation_id: Optional[int] = None
    preset_settlement_mode: Optional[str] = None
    preset_amount: Optional[float] = None
    preset_wallet: Optional[str] = None
    preset_category: Optional[str] = None
    preset_recurring: Optional[bool] = None


class CategoryConfigInput(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    scope: CategoryScope
    type: str = Field(min_length=1)
    color_token: str = Field(min_length=1)
    icon_token: str = Field(min_length=1)
    active: bool = True


class TagConfigInput(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    color_token: str = Field(min_length=1)
    active: bool = True
    command_enabled: bool = False
    preset_transaction_kind: Optional[TransactionKind] = None
    preset_fixed_income_source_id: Optional[int] = None
    preset_obligation_id: Optional[int] = None
    preset_settlement_mode: Optional[str] = None
    preset_amount: Optional[float] = None
    preset_wallet: Optional[str] = None
    preset_category: Optional[str] = None
    preset_recurring: Optional[bool] = None


class CreditCardBase(BaseModel):
    label: str = Field(min_length=1)
    last4: str = Field(min_length=4, max_length=4)
    closing_day: int = Field(ge=1, le=31)
    due_day: int = Field(ge=1, le=31)
    limit_amount: float = Field(gt=0)
    active: bool = True


class CreditCardCreate(CreditCardBase):
    pass


class CreditCard(CreditCardBase):
    id: int


class CreditCardStatementItemInput(BaseModel):
    obligation_id: int
    amount: float = Field(gt=0)


class CreditCardStatementItem(CreditCardStatementItemInput):
    obligation_label: str


class CreditCardStatementBase(BaseModel):
    credit_card_id: int
    statement_date: date
    due_date: date
    period_year: int = Field(ge=2000, le=2100)
    period_month: int = Field(ge=1, le=12)
    statement_amount: float = Field(gt=0)
    notes: str = ''


class CreditCardStatementCreate(CreditCardStatementBase):
    items: list[CreditCardStatementItemInput] = Field(default_factory=list)


class CreditCardStatement(CreditCardStatementBase):
    id: int
    card_label: str
    card_last4: str
    paid_amount: float = 0
    remaining_amount: float = 0
    fixed_items_total: float = 0
    fixed_items_paid_amount: float = 0
    personal_paid_amount: float = 0
    payment_status: str = 'Pendiente'
    utilization_ratio: float = 0
    items: list[CreditCardStatementItem] = Field(default_factory=list)


class CreditCardAlert(BaseModel):
    statement_id: int
    credit_card_id: int
    card_label: str
    card_last4: str
    title: str
    detail: str
    severity: str
    days_until_due: int
    remaining_amount: float


class AllocationSuggestion(BaseModel):
    for_obligations: float
    for_goals: float
    for_personal: float
    rationale: str


class QuincenaReserveView(BaseModel):
    label: str
    amount: float
    detail: str


class WalletBalanceView(BaseModel):
    label: str
    amount: float


class BucketOverview(BaseModel):
    label: str
    reserved: float
    total: float


class InsightView(BaseModel):
    title: str
    body: str


class CategorySpendComparison(BaseModel):
    label: str
    color_token: str
    icon_token: str
    current_amount: float
    previous_amount: float


class DashboardSummary(BaseModel):
    safe_personal_available: float
    fixed_income_expected: float
    income_reported_this_month: float
    free_margin_target: float
    free_margin_available_now: float
    current_month_expense_total: float
    previous_month_expense_total: float
    monthly_fixed_outflow_total: float
    reserve_per_quincena: float
    pending_obligations_total: float
    obligations_target: float
    obligations_reserved: float
    goals_target: float
    goals_reserved: float
    personal_spent_this_month: float
    recommended_personal_budget_this_month: float
    remaining_personal_recommended_this_month: float
    income_gap: float
    quincena_coverage: float
    latest_income_amount: float
    latest_income_suggestion: AllocationSuggestion
    quincena_reserve_views: list[QuincenaReserveView]
    wallet_balances: list[WalletBalanceView]
    bucket_overviews: list[BucketOverview]
    expense_comparisons: list[CategorySpendComparison]
    credit_card_alerts: list[CreditCardAlert]
    generated_insights: list[InsightView]


class BootstrapResponse(BaseModel):
    setup_complete: bool
    theme_id: str
    current_username: str
    current_user_role: UserRole
    can_manage_users: bool
    can_edit_data: bool
    users: list['UserSummary']
    audit_events: list['AuditEvent']
    fixed_income_sources: list[FixedIncomeSource]
    obligations: list[Obligation]
    credit_cards: list[CreditCard]
    credit_card_statements: list[CreditCardStatement]
    transactions: list[Transaction]
    categories: list[CategoryConfig]
    tags: list[TagConfig]
    wallets: list[str]
    dashboard: DashboardSummary


class FlutterImportSummary(BaseModel):
    fixed_income_sources: int
    obligations: int
    transactions: int
    categories: int
    tags: int
    replace_existing: bool


class InitialSetupPayload(BaseModel):
    fixed_income_sources: list[FixedIncomeSourceCreate]
    obligations: list[ObligationCreate]


class UserSummary(BaseModel):
    id: int
    username: str
    role: UserRole
    active: bool
    created_by_username: Optional[str] = None


class AuditEvent(BaseModel):
    id: int
    actor_username: str
    action: str
    target_type: str
    target_value: str
    detail: str
    created_at_iso: str


class AuthStatus(BaseModel):
    authenticated: bool
    has_users: bool
    admin_bootstrap_required: bool
    owner_bootstrap_enabled: bool = False
    admin_bootstrap_code_path: Optional[str] = None
    owner_bootstrap_warning: Optional[str] = None
    setup_complete: bool
    username: Optional[str] = None
    role: Optional[UserRole] = None
    can_edit_data: bool = False
    can_manage_users: bool = False


class OwnerPanelResponse(BaseModel):
    current_username: str
    current_user_role: UserRole
    users: list['UserSummary']
    audit_events: list['AuditEvent']


class LoginRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=4)
    device_name: str = Field(default='Navegador local', min_length=1)


class LoginResponse(BaseModel):
    authenticated: bool
    has_users: bool
    setup_complete: bool
    username: str
    role: UserRole
    can_edit_data: bool
    can_manage_users: bool
    session_token: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=4)
    role: UserRole = UserRole.operator


class UserAccessUpdateRequest(BaseModel):
    role: UserRole
    active: bool


class AdminBootstrapRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=4)
    bootstrap_code: str = Field(min_length=8)
    device_name: str = Field(default='Navegador local', min_length=1)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=4)
    new_password: str = Field(min_length=4)


class ThemePreferenceUpdate(BaseModel):
    theme_id: str = Field(min_length=1)