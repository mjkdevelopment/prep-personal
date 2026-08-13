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
}

export interface Obligation {
  id: number
  label: string
  amount: number
  category_id: string | null
  cadence: FixedIncomeCadence
  due_day: number
  due_weekday: number | null
  kind: string
  status: string
}

export interface Transaction {
  id: number
  kind: TransactionKind
  amount: number
  wallet: string
  category: string
  tags: string[]
  notes: string
  date: string
  recurring: boolean
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
  admin_bootstrap_code_path: string | null
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

export type TransactionInput = Omit<Transaction, 'id'>
export type FixedIncomeSourceInput = Omit<FixedIncomeSource, 'id'>
export type ObligationInput = Omit<Obligation, 'id'>