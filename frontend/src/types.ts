export type TransactionKind = 'ingreso' | 'gasto' | 'transferencia' | 'ahorro' | 'inversion' | 'deuda'
export type FixedIncomeCadence = 'monthly' | 'biweekly' | 'weekly'
export type CategoryScope = 'income' | 'expense'
export type UserRole = 'owner' | 'admin' | 'operator' | 'viewer'

export interface FixedIncomeSource {
  id: number
  label: string
  amount: number
  cadence: FixedIncomeCadence
  expected_day: number
  expected_weekday: number | null
  wallet: string
  active: boolean
  current_period_expected_amount: number
  current_period_recorded_amount: number
  current_period_balance: number
}

export interface Obligation {
  id: number
  label: string
  amount: number
  category_id: string | null
  credit_card_id: number | null
  cadence: FixedIncomeCadence
  due_day: number
  due_weekday: number | null
  kind: string
  status: string
  current_period_expected_amount: number
  current_period_recorded_amount: number
  current_period_balance: number
  current_period_status: string
}

export interface Transaction {
  id: number
  kind: TransactionKind
  amount: number
  wallet: string
  category: string
  fixed_income_source_id: number | null
  obligation_id: number | null
  credit_card_statement_id: number | null
  tags: string[]
  notes: string
  date: string
  recurring: boolean
}

export interface CreditCard {
  id: number
  label: string
  last4: string
  closing_day: number
  due_day: number
  limit_amount: number
  active: boolean
}

export interface CreditCardStatementItem {
  obligation_id: number
  obligation_label: string
  amount: number
}

export interface CreditCardStatement {
  id: number
  credit_card_id: number
  statement_date: string
  due_date: string
  period_year: number
  period_month: number
  statement_amount: number
  notes: string
  card_label: string
  card_last4: string
  paid_amount: number
  remaining_amount: number
  fixed_items_total: number
  fixed_items_paid_amount: number
  personal_paid_amount: number
  payment_status: string
  utilization_ratio: number
  items: CreditCardStatementItem[]
}

export interface CreditCardAlert {
  statement_id: number
  credit_card_id: number
  card_label: string
  card_last4: string
  title: string
  detail: string
  severity: string
  days_until_due: number
  remaining_amount: number
}

export interface CategoryConfig {
  id: string
  label: string
  scope: CategoryScope
  type: string
  color_token: string
  icon_token: string
  active: boolean
}

export interface TagConfig {
  id: string
  label: string
  color_token: string
  active: boolean
  command_enabled: boolean
  preset_transaction_kind: TransactionKind | null
  preset_fixed_income_source_id: number | null
  preset_obligation_id: number | null
  preset_settlement_mode: 'partial' | 'complete' | null
  preset_amount: number | null
  preset_wallet: string | null
  preset_category: string | null
  preset_recurring: boolean | null
}

export type CategoryConfigInput = CategoryConfig
export type TagConfigInput = TagConfig

export interface AllocationSuggestion {
  for_obligations: number
  for_goals: number
  for_personal: number
  rationale: string
}

export interface QuincenaReserveView {
  label: string
  amount: number
  detail: string
}

export interface WalletBalanceView {
  label: string
  amount: number
  expected_income_amount: number
  reported_income_amount: number
  pending_income_amount: number
}

export interface BucketOverview {
  label: string
  reserved: number
  total: number
}

export interface InsightView {
  title: string
  body: string
}

export interface CategorySpendComparison {
  label: string
  color_token: string
  icon_token: string
  current_amount: number
  previous_amount: number
}

export interface DashboardSummary {
  safe_personal_available: number
  fixed_income_expected: number
  income_reported_this_month: number
  free_margin_target: number
  free_margin_available_now: number
  current_month_expense_total: number
  previous_month_expense_total: number
  monthly_fixed_outflow_total: number
  reserve_per_quincena: number
  pending_obligations_total: number
  obligations_target: number
  obligations_reserved: number
  goals_target: number
  goals_reserved: number
  personal_spent_this_month: number
  recommended_personal_budget_this_month: number
  remaining_personal_recommended_this_month: number
  income_gap: number
  quincena_coverage: number
  latest_income_amount: number
  latest_income_suggestion: AllocationSuggestion
  quincena_reserve_views: QuincenaReserveView[]
  wallet_balances: WalletBalanceView[]
  bucket_overviews: BucketOverview[]
  expense_comparisons: CategorySpendComparison[]
  credit_card_alerts: CreditCardAlert[]
  generated_insights: InsightView[]
}

export interface BootstrapResponse {
  setup_complete: boolean
  theme_id: string
  current_username: string
  current_user_role: UserRole
  can_manage_users: boolean
  can_edit_data: boolean
  users: UserSummary[]
  audit_events: AuditEvent[]
  fixed_income_sources: FixedIncomeSource[]
  obligations: Obligation[]
  credit_cards: CreditCard[]
  credit_card_statements: CreditCardStatement[]
  transactions: Transaction[]
  categories: CategoryConfig[]
  tags: TagConfig[]
  wallets: string[]
  dashboard: DashboardSummary
}

export interface FlutterImportSummary {
  fixed_income_sources: number
  obligations: number
  transactions: number
  categories: number
  tags: number
  replace_existing: boolean
}

export interface InitialSetupPayload {
  fixed_income_sources: FixedIncomeSourceInput[]
  obligations: ObligationInput[]
}

export interface AuthStatus {
  authenticated: boolean
  has_users: boolean
  admin_bootstrap_required: boolean
  owner_bootstrap_enabled: boolean
  admin_bootstrap_code_path: string | null
  owner_bootstrap_warning: string | null
  setup_complete: boolean
  username: string | null
  role: UserRole | null
  can_edit_data: boolean
  can_manage_users: boolean
}

export interface OwnerPanelResponse {
  current_username: string
  current_user_role: UserRole
  users: UserSummary[]
  audit_events: AuditEvent[]
}

export interface LoginResponse {
  authenticated: boolean
  has_users: boolean
  setup_complete: boolean
  username: string
  role: UserRole
  can_edit_data: boolean
  can_manage_users: boolean
  session_token: string
}

export interface UserSummary {
  id: number
  username: string
  role: UserRole
  active: boolean
  created_by_username: string | null
}

export interface AuditEvent {
  id: number
  actor_username: string
  action: string
  target_type: string
  target_value: string
  detail: string
  created_at_iso: string
}

export interface UserAccessUpdateInput {
  role: UserRole
  active: boolean
}

export interface TransactionInput {
  kind: TransactionKind
  amount: number
  wallet: string
  category: string
  fixed_income_source_id: number | null
  obligation_id: number | null
  credit_card_statement_id: number | null
  tags: string[]
  notes: string
  date: string
  recurring: boolean
}

export interface CreditCardInput {
  label: string
  last4: string
  closing_day: number
  due_day: number
  limit_amount: number
  active: boolean
}

export interface FixedIncomeSourceInput {
  label: string
  amount: number
  cadence: FixedIncomeCadence
  expected_day: number
  expected_weekday: number | null
  wallet: string
  active: boolean
}

export interface ObligationInput {
  label: string
  amount: number
  category_id: string | null
  credit_card_id: number | null
  cadence: FixedIncomeCadence
  due_day: number
  due_weekday: number | null
  kind: string
  status: string
}

export interface CreditCardStatementItemInput {
  obligation_id: number
  amount: number
}

export interface CreditCardStatementInput {
  credit_card_id: number | null
  statement_date: string
  due_date: string
  period_year: number
  period_month: number
  statement_amount: number
  notes: string
  items: CreditCardStatementItemInput[]
}