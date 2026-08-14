import { useEffect, useMemo, useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from 'react'
import './App.css'
import {
  bootstrapOwner,
  changePassword,
  clearSessionToken,
  completeInitialSetup,
  createCreditCard,
  createCreditCardStatement,
  createUser,
  createFixedIncomeSource,
  createObligation,
  createTransaction,
  deleteCategory,
  deleteCreditCard,
  deleteCreditCardStatement,
  deleteFixedIncomeSource,
  deleteObligation,
  deleteTag,
  deleteTransaction,
  deleteUser,
  fetchAuthStatus,
  fetchBootstrap,
  fetchIncomeSuggestion,
  fetchOwnerPanel,
  importFlutterDatabase,
  login,
  loginOwner,
  logout,
  resetInitialSetup,
  updateThemePreference,
  updateUserAccess,
  updateCreditCard,
  updateCreditCardStatement,
  updateFixedIncomeSource,
  updateObligation,
  updateTransaction,
  upsertCategory,
  upsertTag,
} from './api'
import { applyTheme, getStoredTheme, palettes } from './themes'
import type {
  AllocationSuggestion,
  AuthStatus,
  AuditEvent,
  BootstrapResponse,
  CategoryConfig,
  CategoryConfigInput,
  CreditCard,
  CreditCardInput,
  CreditCardStatement,
  CreditCardStatementInput,
  FixedIncomeCadence,
  FixedIncomeSource,
  FixedIncomeSourceInput,
  FlutterImportSummary,
  InitialSetupPayload,
  LoginResponse,
  Obligation,
  ObligationInput,
  OwnerPanelResponse,
  TagConfig,
  TagConfigInput,
  Transaction,
  TransactionInput,
  TransactionKind,
  UserRole,
} from './types'
import { currency, formatDateInput } from './utils'
import { colorTokens, iconGlyph, iconLabel, iconTokens, slugify, tokenColor } from './visuals'

type AppTab = 'dashboard' | 'transactions' | 'base' | 'settings'
type LinkedSettlementMode = 'partial' | 'complete'

const formatDateOnlyValue = (value: Date | string): string => {
  const date = typeof value === 'string' ? new Date(value) : value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const cardCycleDueDate = (statementDate: string, dueDay: number): string => {
  const base = statementDate ? new Date(`${statementDate}T00:00:00`) : new Date()
  const nextMonth = new Date(base.getFullYear(), base.getMonth() + 1, 1)
  const lastDay = new Date(nextMonth.getFullYear(), nextMonth.getMonth() + 1, 0).getDate()
  return formatDateOnlyValue(new Date(nextMonth.getFullYear(), nextMonth.getMonth(), Math.min(dueDay, lastDay)))
}

const appTabs: Array<{ id: AppTab; label: string }> = [
  { id: 'dashboard', label: 'Resumen' },
  { id: 'transactions', label: 'Movimientos' },
  { id: 'base', label: 'Base' },
  { id: 'settings', label: 'Ajustes' },
]

const normalizeTagLabel = (value: string): string => value.trim().replace(/^#+/, '')

const sameTagLabel = (left: string, right: string): boolean => normalizeTagLabel(left).toLowerCase() === normalizeTagLabel(right).toLowerCase()

const findTagByLabel = (tags: TagConfig[], label: string): TagConfig | null => {
  const normalized = normalizeTagLabel(label)
  if (!normalized) {
    return null
  }

  return tags.find((tag) => sameTagLabel(tag.label, normalized)) ?? null
}

const commandTagColor = (kind: TransactionKind): string => {
  if (kind === 'ingreso') {
    return 'emerald'
  }
  if (kind === 'gasto') {
    return 'terracotta'
  }
  if (kind === 'inversion') {
    return 'sky'
  }
  if (kind === 'deuda') {
    return 'plum'
  }
  if (kind === 'ahorro') {
    return 'sage'
  }
  return 'petrol'
}

const helpSections: Array<{ title: string; items: string[] }> = [
  {
    title: 'Resumen',
    items: [
      'Te da una lectura rapida del mes: gasto, cobertura y disponible sugerido.',
      'Margen libre muestra el excedente del mes y Disponible hoy refleja solo lo ya ingresado.',
      'El grafico destaca en que categorias se esta yendo tu dinero.',
      'Insights resume senales utiles para decidir con mas criterio.',
    ],
  },
  {
    title: 'Movimientos',
    items: [
      'Registra ingresos, gastos y movimientos de orden financiero diario.',
      'Las etiquetas te ayudan a leer patrones sin sobrecargar la vista principal.',
      'Cuando entra dinero, Gride Ledger propone una distribucion equilibrada.',
    ],
  },
  {
    title: 'Base',
    items: [
      'Aqui defines la estructura fija que sostiene tu planeacion mensual.',
      'Los compromisos recurrentes sirven para medir cobertura real, no intuicion.',
      'Si necesitas recomenzar, puedes volver al asistente inicial desde Ajustes.',
    ],
  },
  {
    title: 'Ajustes',
    items: [
      'Controla apariencia, catalogos y mantenimiento desde un solo lugar.',
      'Categorias y tags adaptan la app a tu lenguaje financiero real.',
      'La migracion te permite traer historial previo sin reconstruir todo a mano.',
    ],
  },
  {
    title: 'Usuarios y seguridad',
    items: [
      'La cuenta administradora conserva el control de altas del equipo.',
      'La sesion se mantiene en este navegador hasta que la cierres o cambies la contrasena.',
      'La primera activacion administrativa exige el codigo local de bootstrap.',
    ],
  },
]

function BrandLogo({ dark = false, markOnly = false, className = '' }: { dark?: boolean; markOnly?: boolean; className?: string }) {
  const src = markOnly
    ? dark ? '/branding/gride-ledger-symbol-white.png' : '/branding/gride-ledger-symbol.png'
    : dark ? '/branding/gride-ledger-logo-horizontal-white.png' : '/branding/gride-ledger-logo-horizontal.png'
  const alt = markOnly ? 'Gride Ledger' : 'Gride Ledger logo'
  return <img src={src} alt={alt} className={className} />
}

const emptyTransaction = (wallet = 'Banco', category = ''): TransactionInput => ({
  kind: 'ingreso',
  amount: 0,
  wallet,
  category,
  fixed_income_source_id: null,
  obligation_id: null,
  credit_card_statement_id: null,
  tags: [],
  notes: '',
  date: formatDateInput(new Date().toISOString()),
  recurring: false,
})

const emptyFixedIncome = (wallet = 'Banco'): FixedIncomeSourceInput => ({
  label: '',
  amount: 0,
  cadence: 'monthly',
  expected_day: 15,
  expected_weekday: null,
  wallet,
  active: true,
})

const emptyObligation = (categoryId = 'casa'): ObligationInput => ({
  label: '',
  amount: 0,
  category_id: categoryId,
  credit_card_id: null,
  cadence: 'monthly',
  due_day: 15,
  due_weekday: null,
  kind: 'Fija',
  status: 'Pendiente',
})

const emptyCreditCard = (): CreditCardInput => ({
  label: '',
  last4: '',
  closing_day: 25,
  due_day: 15,
  limit_amount: 0,
  active: true,
})

const emptyCreditCardStatement = (): CreditCardStatementInput => {
  const now = new Date()
  return {
    credit_card_id: null,
    statement_date: formatDateOnlyValue(now),
    due_date: formatDateOnlyValue(new Date(now.getFullYear(), now.getMonth() + 1, 15)),
    period_year: now.getFullYear(),
    period_month: now.getMonth() + 1,
    statement_amount: 0,
    notes: '',
    items: [],
  }
}

const emptyCategory = (scope: 'income' | 'expense' = 'expense'): CategoryConfigInput => ({
  id: '',
  label: '',
  scope,
  type: scope === 'income' ? 'Ingreso' : 'Variable',
  color_token: 'gold',
  icon_token: 'receipt',
  active: true,
})

const emptyTag = (): TagConfigInput => ({
  id: '',
  label: '',
  color_token: 'sage',
  active: true,
  command_enabled: false,
  preset_transaction_kind: null,
  preset_fixed_income_source_id: null,
  preset_obligation_id: null,
  preset_settlement_mode: null,
  preset_amount: null,
  preset_wallet: null,
  preset_category: null,
  preset_recurring: null,
})

const roleLabels: Record<UserRole, string> = {
  owner: 'Owner',
  admin: 'Administrador',
  operator: 'Operador',
  viewer: 'Consulta',
}

const auditActionLabels: Record<string, string> = {
  bootstrap_admin: 'Alta inicial de administrador',
  create_user: 'Creacion de usuario',
  update_user_access: 'Cambio de acceso',
  update_theme: 'Cambio de tema',
  import_flutter_db: 'Importacion de base',
  complete_setup: 'Wizard completado',
  reset_setup: 'Reinicio de configuracion',
}

const transactionKindLabels: Record<TransactionKind, string> = {
  ingreso: 'Ingreso',
  gasto: 'Gasto',
  ahorro: 'Ahorro',
  inversion: 'Inversion',
  deuda: 'Deuda',
  transferencia: 'Transferencia',
}

function deriveObligationKind(payload: ObligationInput, categories: CategoryConfig[]): ObligationInput {
  const category = categories.find((item) => item.id === payload.category_id)
  return { ...payload, kind: category?.type ?? payload.kind }
}

function categoryLabelById(categories: CategoryConfig[], categoryId: string | null | undefined): string {
  if (!categoryId) {
    return ''
  }
  return categories.find((item) => item.id === categoryId)?.label ?? ''
}

function resolveErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) {
    return fallback
  }

  try {
    const parsed = JSON.parse(error.message) as { detail?: unknown }
    if (typeof parsed.detail === 'string' && parsed.detail.trim().length > 0) {
      return parsed.detail
    }
    if (Array.isArray(parsed.detail)) {
      const messages = parsed.detail
        .map((item) => {
          if (typeof item === 'string') {
            return item
          }
          if (item && typeof item === 'object') {
            const detail = item as { msg?: unknown; loc?: unknown }
            const message = typeof detail.msg === 'string' ? detail.msg : null
            const location = Array.isArray(detail.loc) ? detail.loc.join(' > ') : null
            if (message && location) {
              return `${location}: ${message}`
            }
            return message
          }
          return null
        })
        .filter((item): item is string => Boolean(item && item.trim().length > 0))
      if (messages.length > 0) {
        return messages.join(' | ')
      }
    }
    if (typeof error.message === 'string' && error.message.trim().length > 0) {
      return error.message
    }
    return fallback
  } catch {
    return error.message || fallback
  }
}

function findCategoryByLabel(categories: CategoryConfig[], label: string, scope?: CategoryConfig['scope']): CategoryConfig | undefined {
  return categories.find((item) => item.label === label && (scope ? item.scope === scope : true))
}

function walletVisual(wallet: string): { icon: string; color: string } {
  switch (wallet) {
    case 'Efectivo':
      return { icon: 'paid', color: 'gold' }
    case 'Banco':
      return { icon: 'account_balance', color: 'petrol' }
    case 'Cooperativa':
      return { icon: 'group', color: 'sage' }
    default:
      return { icon: 'briefcase', color: 'sky' }
  }
}

function cadencePaymentsPerMonth(cadence: FixedIncomeCadence): number {
  switch (cadence) {
    case 'weekly':
      return 4
    case 'biweekly':
      return 2
    default:
      return 1
  }
}

function cadenceExpectedMonthlyAmount(amount: number, cadence: FixedIncomeCadence): number {
  return amount * cadencePaymentsPerMonth(cadence)
}

function cadenceProjectionCopy(amount: number, cadence: FixedIncomeCadence, singularLabel: string): string {
  const payments = cadencePaymentsPerMonth(cadence)
  const monthlyExpected = cadenceExpectedMonthlyAmount(amount, cadence)
  if (payments === 1) {
    return `Se espera 1 ${singularLabel} de ${currency(amount)} al mes.`
  }
  return `Se esperan ${payments} ${singularLabel}s de ${currency(amount)}. Base mensual: ${currency(monthlyExpected)}.`
}

const weekdayLabels: Record<number, string> = {
  1: 'Lunes',
  2: 'Martes',
  3: 'Miercoles',
  4: 'Jueves',
  5: 'Viernes',
  6: 'Sabado',
  7: 'Domingo',
}

function clampDayOfMonth(value: number): number {
  if (!Number.isFinite(value)) {
    return 15
  }
  return Math.min(31, Math.max(1, Math.trunc(value)))
}

function clampWeekday(value: number | null | undefined): number {
  if (!value || !Number.isFinite(value)) {
    return 1
  }
  return Math.min(7, Math.max(1, Math.trunc(value)))
}

function cadenceScheduleCopy(cadence: FixedIncomeCadence, dayOfMonth: number, weekday: number | null | undefined): string {
  switch (cadence) {
    case 'weekly':
      return `Semanal · ${weekdayLabels[clampWeekday(weekday)]}`
    case 'biweekly':
      return 'Quincenal · dias 15 y 30'
    default:
      return `Mensual · dia ${clampDayOfMonth(dayOfMonth)}`
  }
}

function normalizeFixedIncomeCadenceFields(payload: FixedIncomeSourceInput): FixedIncomeSourceInput {
  switch (payload.cadence) {
    case 'weekly':
      return { ...payload, expected_day: 1, expected_weekday: clampWeekday(payload.expected_weekday) }
    case 'biweekly':
      return { ...payload, expected_day: 15, expected_weekday: null }
    default:
      return { ...payload, expected_day: clampDayOfMonth(payload.expected_day), expected_weekday: null }
  }
}

function normalizeObligationCadenceFields(payload: ObligationInput): ObligationInput {
  switch (payload.cadence) {
    case 'weekly':
      return { ...payload, due_day: 1, due_weekday: clampWeekday(payload.due_weekday) }
    case 'biweekly':
      return { ...payload, due_day: 15, due_weekday: null }
    default:
      return { ...payload, due_day: clampDayOfMonth(payload.due_day), due_weekday: null }
  }
}

function VisualBadge({ iconToken, colorToken, narrow = false }: { iconToken: string; colorToken: string; narrow?: boolean }) {
  return <span className={narrow ? 'icon-badge narrow' : 'icon-badge'} style={{ background: `${tokenColor(colorToken)}22`, color: tokenColor(colorToken) }}>{iconGlyph(iconToken)}</span>
}

function TagPill({ label, colorToken }: { label: string; colorToken: string }) {
  return <span className="history-tag" style={{ background: `${tokenColor(colorToken)}18`, color: tokenColor(colorToken), borderColor: `${tokenColor(colorToken)}33` }}>#{label}</span>
}

function compactInsightBody(body: string): string {
  const normalized = body.trim()
  if (!normalized) {
    return ''
  }

  const firstSentence = normalized.match(/.*?[.!?](?:\s|$)/)?.[0]?.trim()
  if (firstSentence && firstSentence.length <= 110) {
    return firstSentence
  }

  return normalized.length <= 110 ? normalized : `${normalized.slice(0, 107).trimEnd()}...`
}

function insightTone(insight: BootstrapResponse['dashboard']['generated_insights'][number], index: number): { label: string; className: string } {
  const haystack = `${insight.title} ${insight.body}`.toLowerCase()

  if (/(encima|riesgo|alerta|subio|desvio|pendiente)/.test(haystack)) {
    return { label: 'Atencion', className: 'warning' }
  }

  if (/(puedes|oportunidad|aumentar|mejora|ajuste)/.test(haystack)) {
    return { label: 'Impulso', className: 'positive' }
  }

  if (/(control|cobertura|estable|cubierto)/.test(haystack)) {
    return { label: 'Control', className: 'calm' }
  }

  return index % 2 === 0 ? { label: 'Pulso', className: 'neutral' } : { label: 'Clave', className: 'calm' }
}

function App() {
  const [routePath, setRoutePath] = useState(() => typeof window === 'undefined' ? '/' : window.location.pathname)
  const isOwnerRoute = routePath.startsWith('/owner')
  const isLoginRoute = routePath === '/login'
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null)
  const [data, setData] = useState<BootstrapResponse | null>(null)
  const [ownerData, setOwnerData] = useState<OwnerPanelResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<AppTab>('dashboard')
  const [selectedTheme, setSelectedTheme] = useState(getStoredTheme())
  const [transactionForm, setTransactionForm] = useState<TransactionInput>(emptyTransaction())
  const [fixedIncomeForm, setFixedIncomeForm] = useState<FixedIncomeSourceInput>(emptyFixedIncome())
  const [obligationForm, setObligationForm] = useState<ObligationInput>(emptyObligation())
  const [creditCardForm, setCreditCardForm] = useState<CreditCardInput>(emptyCreditCard())
  const [creditCardStatementForm, setCreditCardStatementForm] = useState<CreditCardStatementInput>(emptyCreditCardStatement())
  const [categoryForm, setCategoryForm] = useState<CategoryConfigInput>(emptyCategory())
  const [tagForm, setTagForm] = useState<TagConfigInput>(emptyTag())
  const [tagCommandInput, setTagCommandInput] = useState('')
  const [saveAsCommandTag, setSaveAsCommandTag] = useState(false)
  const [userForm, setUserForm] = useState<{ username: string; password: string; role: UserRole }>({ username: '', password: '', role: 'operator' })
  const [passwordForm, setPasswordForm] = useState({ currentPassword: '', newPassword: '' })
  const [transactionSettlementMode, setTransactionSettlementMode] = useState<LinkedSettlementMode>('partial')
  const [editingTransactionId, setEditingTransactionId] = useState<number | null>(null)
  const [editingFixedIncomeId, setEditingFixedIncomeId] = useState<number | null>(null)
  const [editingObligationId, setEditingObligationId] = useState<number | null>(null)
  const [editingCreditCardId, setEditingCreditCardId] = useState<number | null>(null)
  const [editingCreditCardStatementId, setEditingCreditCardStatementId] = useState<number | null>(null)
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null)
  const [editingTagId, setEditingTagId] = useState<string | null>(null)
  const [suggestion, setSuggestion] = useState<AllocationSuggestion | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<FlutterImportSummary | null>(null)

  useEffect(() => {
    applyTheme(selectedTheme)
  }, [selectedTheme])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    const handlePopState = () => {
      setRoutePath(window.location.pathname)
    }

    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const navigate = (path: string, mode: 'push' | 'replace' = 'push') => {
    if (typeof window === 'undefined') {
      return
    }
    if (window.location.pathname === path) {
      setRoutePath(path)
      return
    }

    if (mode === 'replace') {
      window.history.replaceState(null, '', path)
    } else {
      window.history.pushState(null, '', path)
    }
    setRoutePath(path)
  }

  useEffect(() => {
    if (typeof document === 'undefined') {
      return
    }

    if (authStatus?.authenticated && data?.setup_complete) {
      document.body.dataset.appTab = activeTab
      return () => {
        delete document.body.dataset.appTab
      }
    }

    delete document.body.dataset.appTab
    return undefined
  }, [activeTab, authStatus?.authenticated, data?.setup_complete])

  const activeCategories = useMemo(() => data?.categories.filter((item) => item.active) ?? [], [data])
  const incomeCategories = useMemo(() => activeCategories.filter((item) => item.scope === 'income'), [activeCategories])
  const expenseCategories = useMemo(() => activeCategories.filter((item) => item.scope === 'expense'), [activeCategories])
  const defaultWallet = data?.wallets[0] ?? 'Banco'
  const defaultIncomeCategory = incomeCategories[0]?.label ?? ''
  const defaultExpenseCategoryId = expenseCategories[0]?.id ?? 'casa'
  const canEditData = data?.can_edit_data ?? false

  const load = async () => {
    if (isOwnerRoute) {
      const next = await fetchOwnerPanel()
      setOwnerData(next)
      setData(null)
      setError(null)
      return
    }

    const next = await fetchBootstrap()
    setData(next)
    setOwnerData(null)
    setSelectedTheme(next.theme_id)
    setError(null)
    const nextIncomeCategory = next.categories.find((item) => item.scope === 'income' && item.active)?.label ?? ''
    const nextExpenseCategoryId = next.categories.find((item) => item.scope === 'expense' && item.active)?.id ?? 'casa'
    const nextWallet = next.wallets[0] ?? 'Banco'
    setTransactionForm((current) => ({ ...current, wallet: current.wallet || nextWallet, category: current.category || nextIncomeCategory }))
    setFixedIncomeForm((current) => ({ ...current, wallet: current.wallet || nextWallet }))
    setObligationForm((current) => ({ ...current, category_id: current.category_id || nextExpenseCategoryId }))
  }

  useEffect(() => {
    let cancelled = false

    const boot = async () => {
      setLoading(true)
      try {
        const status = await fetchAuthStatus()
        if (cancelled) {
          return
        }
        setError(null)
        setAuthError(null)
        setAuthStatus(status)
        if (status.authenticated) {
          if (status.role === 'owner' && !isOwnerRoute) {
            navigate('/owner', 'replace')
          }
          if (status.role !== 'owner' && isLoginRoute) {
            navigate('/', 'replace')
          }
          if (isOwnerRoute && status.role !== 'owner') {
            clearSessionToken()
            setAuthStatus({ ...status, authenticated: false, username: null, role: null, can_edit_data: false, can_manage_users: false })
            setData(null)
            setOwnerData(null)
            setAuthError('Este acceso es exclusivo para la cuenta owner.')
            return
          }
          await load()
        } else {
          if (!isOwnerRoute && !isLoginRoute) {
            navigate('/login', 'replace')
          }
          setData(null)
          setOwnerData(null)
        }
      } catch (bootError) {
        if (!cancelled) {
          const message = resolveErrorMessage(bootError, 'No se pudo validar la sesion.')
          if (authStatus?.authenticated) {
            setError(message)
          } else {
            setAuthError(message)
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void boot()
    return () => {
      cancelled = true
    }
  }, [isOwnerRoute])

  useEffect(() => {
    if (!authStatus?.authenticated || transactionForm.kind !== 'ingreso' || transactionForm.amount <= 0) {
      setSuggestion(null)
      return
    }

    let cancelled = false
    void fetchIncomeSuggestion(transactionForm.amount)
      .then((result) => {
        if (!cancelled) {
          setSuggestion(result)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSuggestion(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [authStatus?.authenticated, transactionForm.amount, transactionForm.kind])

  const refreshAfterAuth = async (response?: LoginResponse) => {
    if (response?.role === 'owner') {
      navigate('/owner', 'replace')
    } else {
      navigate('/', 'replace')
    }
    setAuthStatus({
      authenticated: true,
      has_users: response?.has_users ?? true,
      admin_bootstrap_required: false,
      owner_bootstrap_enabled: false,
      admin_bootstrap_code_path: null,
      owner_bootstrap_warning: null,
      setup_complete: response?.setup_complete ?? true,
      username: response?.username ?? null,
      role: response?.role ?? null,
      can_edit_data: response?.can_edit_data ?? false,
      can_manage_users: response?.can_manage_users ?? false,
    })
    await load()
  }

  const handleUserSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      await createUser(userForm.username, userForm.password, userForm.role)
      setUserForm({ username: '', password: '', role: 'operator' })
      await load()
    } catch (userError) {
      setError(resolveErrorMessage(userError, 'No se pudo crear el usuario.'))
    } finally {
      setSaving(false)
    }
  }

  const handleUserAccessUpdate = async (userId: number, role: UserRole, active: boolean) => {
    setSaving(true)
    try {
      await updateUserAccess(userId, { role, active })
      await load()
    } catch (accessError) {
      setError(resolveErrorMessage(accessError, 'No se pudo actualizar el acceso del usuario.'))
    } finally {
      setSaving(false)
    }
  }

  const handleUserDelete = async (userId: number, username: string) => {
    const confirmed = window.confirm(`Se eliminara ${username} junto con sus datos asociados.\n\n¿Deseas continuar?`)
    if (!confirmed) {
      return
    }

    setSaving(true)
    try {
      await deleteUser(userId)
      await load()
    } catch (deleteError) {
      setError(resolveErrorMessage(deleteError, 'No se pudo eliminar el usuario.'))
    } finally {
      setSaving(false)
    }
  }

  const handleTransactionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const normalizedCommandTag = normalizeTagLabel(tagCommandInput)
      const existingCommandTag = data ? findTagByLabel(data.tags, normalizedCommandTag) : null
      const payload: TransactionInput = normalizedCommandTag && !transactionForm.tags.some((item) => sameTagLabel(item, normalizedCommandTag))
        ? { ...transactionForm, tags: [...transactionForm.tags, existingCommandTag?.label ?? normalizedCommandTag] }
        : transactionForm
      const selectedStatement = data?.credit_card_statements.find((item) => item.id === payload.credit_card_statement_id) ?? null
      const selectedCard = data?.credit_cards.find((item) => item.id === selectedStatement?.credit_card_id) ?? null

      if (saveAsCommandTag) {
        if (!normalizedCommandTag) {
          throw new Error('Escribe el nombre del tag comando antes de guardarlo.')
        }

        await upsertTag({
          id: existingCommandTag?.id ?? slugify(normalizedCommandTag),
          label: existingCommandTag?.label ?? normalizedCommandTag,
          color_token: existingCommandTag?.color_token ?? commandTagColor(payload.kind),
          active: true,
          command_enabled: true,
          preset_transaction_kind: payload.kind,
          preset_fixed_income_source_id: payload.kind === 'ingreso' ? payload.fixed_income_source_id : null,
          preset_obligation_id: payload.kind === 'gasto' ? payload.obligation_id : null,
          preset_settlement_mode: payload.kind === 'ingreso' || payload.kind === 'gasto' ? transactionSettlementMode : null,
          preset_amount: payload.amount || null,
          preset_wallet: payload.wallet || null,
          preset_category: payload.category || null,
          preset_recurring: payload.recurring,
        })
      }

      if (editingTransactionId) {
        await updateTransaction(editingTransactionId, payload)
      } else {
        await createTransaction(payload)
      }
      setTransactionForm(emptyTransaction(defaultWallet, defaultIncomeCategory))
      setTransactionSettlementMode('partial')
      setTagCommandInput('')
      setSaveAsCommandTag(false)
      setEditingTransactionId(null)
      await load()
      if (!editingTransactionId && selectedStatement && selectedCard) {
        const ratio = selectedCard.limit_amount <= 0 ? 0 : selectedStatement.statement_amount / selectedCard.limit_amount
        window.alert(ratio <= 0.3 ? `La TC ${selectedCard.last4} quedo en una zona manejable frente a su limite.` : `La TC ${selectedCard.last4} uso una parte alta de su limite en este ciclo. Conviene vigilarla.`)
      }
    } catch (submitError) {
      setError(resolveErrorMessage(submitError, 'No se pudo guardar el movimiento.'))
    } finally {
      setSaving(false)
    }
  }

  const handleFixedIncomeSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = normalizeFixedIncomeCadenceFields(fixedIncomeForm)
      if (editingFixedIncomeId) {
        await updateFixedIncomeSource(editingFixedIncomeId, payload)
      } else {
        await createFixedIncomeSource(payload)
      }
      setFixedIncomeForm(emptyFixedIncome(defaultWallet))
      setEditingFixedIncomeId(null)
      await load()
    } catch (submitError) {
      setError(resolveErrorMessage(submitError, 'No se pudo guardar el ingreso fijo.'))
    } finally {
      setSaving(false)
    }
  }

  const handleObligationSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = deriveObligationKind(normalizeObligationCadenceFields(obligationForm), expenseCategories)
      if (editingObligationId) {
        await updateObligation(editingObligationId, payload)
      } else {
        await createObligation(payload)
      }
      setObligationForm(emptyObligation(defaultExpenseCategoryId))
      setEditingObligationId(null)
      await load()
    } catch (submitError) {
      setError(resolveErrorMessage(submitError, 'No se pudo guardar el gasto fijo.'))
    } finally {
      setSaving(false)
    }
  }

  const handleCreditCardSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = { ...creditCardForm, last4: creditCardForm.last4.trim().slice(-4) }
      if (editingCreditCardId) {
        await updateCreditCard(editingCreditCardId, payload)
      } else {
        await createCreditCard(payload)
      }
      setCreditCardForm(emptyCreditCard())
      setEditingCreditCardId(null)
      await load()
    } catch (submitError) {
      setError(resolveErrorMessage(submitError, 'No se pudo guardar la tarjeta.'))
    } finally {
      setSaving(false)
    }
  }

  const handleCreditCardStatementSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      if (!creditCardStatementForm.credit_card_id) {
        throw new Error('Selecciona primero una tarjeta para el estado de cuenta.')
      }
      const payload = {
        ...creditCardStatementForm,
        items: creditCardStatementForm.items.filter((item) => item.amount > 0),
      }
      if (editingCreditCardStatementId) {
        await updateCreditCardStatement(editingCreditCardStatementId, payload)
      } else {
        await createCreditCardStatement(payload)
      }
      setCreditCardStatementForm(emptyCreditCardStatement())
      setEditingCreditCardStatementId(null)
      await load()
    } catch (submitError) {
      setError(resolveErrorMessage(submitError, 'No se pudo guardar el estado de cuenta.'))
    } finally {
      setSaving(false)
    }
  }

  const handleCategorySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const id = categoryForm.id.trim() || slugify(categoryForm.label)
      await upsertCategory({ ...categoryForm, id, type: categoryForm.scope === 'income' ? 'Ingreso' : categoryForm.type })
      setCategoryForm(emptyCategory())
      setEditingCategoryId(null)
      await load()
    } catch (submitError) {
      setError(resolveErrorMessage(submitError, 'No se pudo guardar la categoria.'))
    } finally {
      setSaving(false)
    }
  }

  const handleTagSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const id = tagForm.id.trim() || slugify(tagForm.label)
      await upsertTag({ ...tagForm, id })
      setTagForm(emptyTag())
      setEditingTagId(null)
      await load()
    } catch (submitError) {
      setError(resolveErrorMessage(submitError, 'No se pudo guardar el tag.'))
    } finally {
      setSaving(false)
    }
  }

  const handleImport = async () => {
    if (!importFile) {
      setError('Selecciona primero un archivo prep_personal.db para importar.')
      return
    }

    setImporting(true)
    try {
      const result = await importFlutterDatabase(importFile, true)
      setImportResult(result)
      setImportFile(null)
      setError(null)
      setActiveTab('dashboard')
      await load()
    } catch (importError) {
      setError(resolveErrorMessage(importError, 'No se pudo importar la base Flutter.'))
    } finally {
      setImporting(false)
    }
  }

  const handleReset = async () => {
    const confirmed = window.confirm('Se borraran ingresos fijos, gastos fijos y transacciones para volver al asistente inicial. Las categorias y tags personalizados se conservan.\n\n¿Deseas reiniciar?')
    if (!confirmed) {
      return
    }

    setSaving(true)
    try {
      await resetInitialSetup()
      setActiveTab('dashboard')
      setTransactionForm(emptyTransaction(defaultWallet, defaultIncomeCategory))
      setFixedIncomeForm(emptyFixedIncome(defaultWallet))
      setObligationForm(emptyObligation(defaultExpenseCategoryId))
      setCreditCardForm(emptyCreditCard())
      setCreditCardStatementForm(emptyCreditCardStatement())
      await load()
    } catch (resetError) {
      setError(resolveErrorMessage(resetError, 'No se pudo reiniciar la configuracion.'))
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      await changePassword(passwordForm.currentPassword, passwordForm.newPassword)
      clearSessionToken()
      if (!isOwnerRoute) {
        navigate('/login', 'replace')
      }
      setAuthStatus((current) => ({ authenticated: false, has_users: current?.has_users ?? true, admin_bootstrap_required: current?.admin_bootstrap_required ?? false, owner_bootstrap_enabled: current?.owner_bootstrap_enabled ?? false, admin_bootstrap_code_path: current?.admin_bootstrap_code_path ?? null, owner_bootstrap_warning: current?.owner_bootstrap_warning ?? null, setup_complete: current?.setup_complete ?? false, username: current?.username ?? null, role: current?.role ?? null, can_edit_data: current?.can_edit_data ?? false, can_manage_users: current?.can_manage_users ?? false }))
      setData(null)
      setOwnerData(null)
      setPasswordForm({ currentPassword: '', newPassword: '' })
      setAuthError('La contrasena fue actualizada. Inicia sesion otra vez con tu usuario en este equipo.')
    } catch (passwordError) {
      setError(resolveErrorMessage(passwordError, 'No se pudo actualizar la contrasena.'))
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = async () => {
    setSaving(true)
    try {
      await logout()
    } catch {
      clearSessionToken()
    } finally {
      if (!isOwnerRoute) {
        navigate('/login', 'replace')
      }
      setAuthStatus((current) => ({ authenticated: false, has_users: current?.has_users ?? true, admin_bootstrap_required: current?.admin_bootstrap_required ?? false, owner_bootstrap_enabled: current?.owner_bootstrap_enabled ?? false, admin_bootstrap_code_path: current?.admin_bootstrap_code_path ?? null, owner_bootstrap_warning: current?.owner_bootstrap_warning ?? null, setup_complete: current?.setup_complete ?? false, username: current?.username ?? null, role: current?.role ?? null, can_edit_data: current?.can_edit_data ?? false, can_manage_users: current?.can_manage_users ?? false }))
      setData(null)
      setOwnerData(null)
      setSaving(false)
    }
  }

  if (loading && authStatus === null) {
    return <div className="screen-state">Cargando acceso seguro...</div>
  }

  if (!authStatus?.authenticated) {
    return (
      <LoginGate
        ownerMode={isOwnerRoute}
        authStatus={authStatus}
        error={authError}
        busy={loading}
        onLogin={async (username, password, bootstrapCode) => {
          setAuthError(null)
          setLoading(true)
          try {
            const deviceName = typeof navigator === 'undefined' ? 'Navegador local' : `${navigator.platform || 'PC'} · navegador local`
            const response = isOwnerRoute
              ? authStatus?.admin_bootstrap_required
                ? await bootstrapOwner(username, password, bootstrapCode ?? '', deviceName)
                : await loginOwner(username, password, deviceName)
              : await login(username, password, deviceName)
            await refreshAfterAuth(response)
          } catch (loginError) {
            setAuthError(resolveErrorMessage(loginError, 'No se pudo iniciar sesion.'))
          } finally {
            setLoading(false)
          }
        }}
      />
    )
  }

  if (loading && !data) {
    return <div className="screen-state">Cargando tablero financiero...</div>
  }

  if (!data) {
    if (isOwnerRoute && ownerData) {
      return (
        <OwnerPanel
          data={ownerData}
          saving={saving}
          error={error}
          userForm={userForm}
          setUserForm={setUserForm}
          onUserSubmit={handleUserSubmit}
          onUpdateUserAccess={handleUserAccessUpdate}
          onDeleteUser={(userId, username) => void handleUserDelete(userId, username)}
          onLogout={() => void handleLogout()}
        />
      )
    }
    return <div className="screen-state error">{error ?? 'No se pudo iniciar la aplicacion.'}</div>
  }

  if (isOwnerRoute) {
    return ownerData ? (
      <OwnerPanel
        data={ownerData}
        saving={saving}
        error={error}
        userForm={userForm}
        setUserForm={setUserForm}
        onUserSubmit={handleUserSubmit}
        onUpdateUserAccess={handleUserAccessUpdate}
        onDeleteUser={(userId, username) => void handleUserDelete(userId, username)}
        onLogout={() => void handleLogout()}
      />
    ) : <div className="screen-state error">{error ?? 'No se pudo iniciar el panel owner.'}</div>
  }

  const categoriesForTransactionKind = transactionForm.kind === 'ingreso' ? incomeCategories : expenseCategories

  return data.setup_complete ? (
    <main className={`app-shell app-shell-${activeTab}`}>
      <section className="hero-panel">
        <div>
          <BrandLogo className="brand-hero-logo" />
          <h1>Tu tablero financiero</h1>
          <div className="hero-meta">
            <span>Cuenta <strong>{data.current_username}</strong></span>
            <span>{roleLabels[data.current_user_role]}</span>
          </div>
        </div>
        <div className="hero-card">
          <BrandLogo dark markOnly className="brand-mark brand-mark-on-dark" />
          <span>Disponible personal</span>
          <strong>{currency(data.dashboard.safe_personal_available)}</strong>
          <p>{currency(data.dashboard.income_reported_this_month)} reportados de {currency(data.dashboard.fixed_income_expected)} esperados.</p>
          <div className="action-row top-gap">
            <button type="button" className="ghost light" onClick={() => void handleLogout()}>Cerrar sesion</button>
          </div>
        </div>
      </section>

      <HelpDock />

      {error ? <div className="banner error">{error}</div> : null}

      <nav className="tab-rail" aria-label="Secciones principales">
        {appTabs.map((tab) => (
          <button key={tab.id} type="button" className={activeTab === tab.id ? 'tab-chip active' : 'tab-chip'} onClick={() => setActiveTab(tab.id)}>
            <div className="tab-chip-top"><strong>{tab.label}</strong></div>
          </button>
        ))}
      </nav>

      {activeTab === 'dashboard' ? <DashboardTab data={data} /> : null}
      {activeTab === 'transactions' ? (
        <TransactionsTab
          data={data}
          canEditData={canEditData}
          saving={saving}
          editingTransactionId={editingTransactionId}
          transactionForm={transactionForm}
          setTransactionForm={setTransactionForm}
          transactionSettlementMode={transactionSettlementMode}
          setTransactionSettlementMode={setTransactionSettlementMode}
          categoriesForTransactionKind={categoriesForTransactionKind}
          suggestion={suggestion}
          onSubmit={handleTransactionSubmit}
          onEdit={(transaction) => {
            setEditingTransactionId(transaction.id)
            setTransactionSettlementMode('partial')
            const presetTag = transaction.tags.map((label) => findTagByLabel(data.tags, label)).find((item) => item?.command_enabled) ?? null
            setTagCommandInput(presetTag ? `#${presetTag.label}` : '')
            setSaveAsCommandTag(Boolean(presetTag))
            setTransactionForm({ ...transaction, date: formatDateInput(transaction.date) })
          }}
          onDelete={async (id) => {
            await deleteTransaction(id)
            await load()
          }}
          onCancelEdit={() => {
            setEditingTransactionId(null)
            setTransactionSettlementMode('partial')
            setTagCommandInput('')
            setSaveAsCommandTag(false)
            setTransactionForm(emptyTransaction(defaultWallet, defaultIncomeCategory))
          }}
          tagCommandInput={tagCommandInput}
          setTagCommandInput={setTagCommandInput}
          saveAsCommandTag={saveAsCommandTag}
          setSaveAsCommandTag={setSaveAsCommandTag}
          onApplyCommandTag={(tag) => {
            setTagCommandInput(`#${tag.label}`)
            if (!tag.command_enabled) {
              return
            }

            setTransactionSettlementMode(tag.preset_settlement_mode ?? 'partial')
            setTransactionForm((current) => {
              const nextKind = tag.preset_transaction_kind ?? current.kind
              const nextTags = current.tags.some((item) => sameTagLabel(item, tag.label)) ? current.tags : [...current.tags, tag.label]

              return {
                ...current,
                kind: nextKind,
                amount: tag.preset_amount ?? current.amount,
                wallet: tag.preset_wallet ?? current.wallet,
                category: tag.preset_category ?? current.category,
                fixed_income_source_id: nextKind === 'ingreso' ? (tag.preset_fixed_income_source_id ?? current.fixed_income_source_id) : null,
                obligation_id: nextKind === 'gasto' ? (tag.preset_obligation_id ?? current.obligation_id) : null,
                credit_card_statement_id: null,
                tags: nextTags,
                date: formatDateInput(new Date().toISOString()),
                recurring: tag.preset_recurring ?? current.recurring,
              }
            })
          }}
        />
      ) : null}
      {activeTab === 'base' ? (
        <BaseTab
          data={data}
          canEditData={canEditData}
          saving={saving}
          fixedIncomeForm={fixedIncomeForm}
          setFixedIncomeForm={setFixedIncomeForm}
          obligationForm={obligationForm}
          setObligationForm={setObligationForm}
          creditCardForm={creditCardForm}
          setCreditCardForm={setCreditCardForm}
          creditCardStatementForm={creditCardStatementForm}
          setCreditCardStatementForm={setCreditCardStatementForm}
          editingFixedIncomeId={editingFixedIncomeId}
          editingObligationId={editingObligationId}
          editingCreditCardId={editingCreditCardId}
          editingCreditCardStatementId={editingCreditCardStatementId}
          expenseCategories={expenseCategories}
          onFixedIncomeSubmit={handleFixedIncomeSubmit}
          onObligationSubmit={handleObligationSubmit}
          onCreditCardSubmit={handleCreditCardSubmit}
          onCreditCardStatementSubmit={handleCreditCardStatementSubmit}
          onEditFixedIncome={(item) => {
            setEditingFixedIncomeId(item.id)
            setFixedIncomeForm({ label: item.label, amount: item.amount, cadence: item.cadence, expected_day: item.expected_day, expected_weekday: item.expected_weekday, wallet: item.wallet, active: item.active })
          }}
          onEditObligation={(item) => {
            setEditingObligationId(item.id)
            setObligationForm({ label: item.label, amount: item.amount, category_id: item.category_id, credit_card_id: item.credit_card_id, cadence: item.cadence, due_day: item.due_day, due_weekday: item.due_weekday, kind: item.kind, status: item.status })
          }}
          onEditCreditCard={(item) => {
            setEditingCreditCardId(item.id)
            setCreditCardForm({ label: item.label, last4: item.last4, closing_day: item.closing_day, due_day: item.due_day, limit_amount: item.limit_amount, active: item.active })
          }}
          onEditCreditCardStatement={(item) => {
            setEditingCreditCardStatementId(item.id)
            setCreditCardStatementForm({
              credit_card_id: item.credit_card_id,
              statement_date: item.statement_date.slice(0, 10),
              due_date: item.due_date.slice(0, 10),
              period_year: item.period_year,
              period_month: item.period_month,
              statement_amount: item.statement_amount,
              notes: item.notes,
              items: item.items.map((statementItem) => ({ obligation_id: statementItem.obligation_id, amount: statementItem.amount })),
            })
          }}
          onDeleteFixedIncome={async (id) => {
            await deleteFixedIncomeSource(id)
            await load()
          }}
          onDeleteObligation={async (id) => {
            await deleteObligation(id)
            await load()
          }}
          onDeleteCreditCard={async (id) => {
            await deleteCreditCard(id)
            await load()
          }}
          onDeleteCreditCardStatement={async (id) => {
            await deleteCreditCardStatement(id)
            await load()
          }}
        />
      ) : null}
      {activeTab === 'settings' ? (
        <SettingsTab
          data={data}
          canEditData={canEditData}
          saving={saving}
          importing={importing}
          selectedTheme={selectedTheme}
          onThemeSelect={async (themeId) => {
            setSelectedTheme(themeId)
            await updateThemePreference(themeId)
            setData((current) => (current ? { ...current, theme_id: themeId } : current))
          }}
          passwordForm={passwordForm}
          setPasswordForm={setPasswordForm}
          categoryForm={categoryForm}
          setCategoryForm={setCategoryForm}
          tagForm={tagForm}
          setTagForm={setTagForm}
          editingCategoryId={editingCategoryId}
          editingTagId={editingTagId}
          importResult={importResult}
          onPasswordSubmit={handlePasswordSubmit}
          onLogout={() => void handleLogout()}
          onCategorySubmit={handleCategorySubmit}
          onTagSubmit={handleTagSubmit}
          onEditCategory={(category) => {
            setEditingCategoryId(category.id)
            setCategoryForm({ ...category })
          }}
          onEditTag={(tag) => {
            setEditingTagId(tag.id)
            setTagForm({ ...tag })
          }}
          onToggleCategory={async (category) => {
            await upsertCategory({ ...category, active: !category.active })
            await load()
          }}
          onToggleTag={async (tag) => {
            await upsertTag({ ...tag, active: !tag.active })
            await load()
          }}
          onDeleteCategory={async (category) => {
            const confirmed = window.confirm(`Se eliminara la categoria ${category.label}. Las obligaciones asociadas quedaran sin categoria.\n\n¿Deseas continuar?`)
            if (!confirmed) {
              return
            }
            await deleteCategory(category.id)
            if (editingCategoryId === category.id) {
              setEditingCategoryId(null)
              setCategoryForm(emptyCategory())
            }
            await load()
          }}
          onDeleteTag={async (tag) => {
            const confirmed = window.confirm(`Se eliminara el tag ${tag.label}.\n\n¿Deseas continuar?`)
            if (!confirmed) {
              return
            }
            await deleteTag(tag.id)
            if (editingTagId === tag.id) {
              setEditingTagId(null)
              setTagForm(emptyTag())
            }
            await load()
          }}
          onImportFileChange={setImportFile}
          onImport={() => void handleImport()}
          onReset={() => void handleReset()}
          resetCategoryForm={() => {
            setEditingCategoryId(null)
            setCategoryForm(emptyCategory())
          }}
          resetTagForm={() => {
            setEditingTagId(null)
            setTagForm(emptyTag())
          }}
        />
      ) : null}
    </main>
  ) : (
    <SetupWizard
      wallets={data.wallets}
      expenseCategories={expenseCategories}
      canEditData={canEditData}
      saving={saving}
      onLogout={() => void handleLogout()}
      onActivate={async (payload) => {
        setSaving(true)
        try {
          const response = await completeInitialSetup(payload)
          setData(response)
          setActiveTab('dashboard')
          setTransactionForm(emptyTransaction(defaultWallet, defaultIncomeCategory))
          setFixedIncomeForm(emptyFixedIncome(defaultWallet))
          setObligationForm(emptyObligation(defaultExpenseCategoryId))
        } finally {
          setSaving(false)
        }
      }}
    />
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return <article className="metric-card"><span className="metric-kicker">{label}</span><strong>{value}</strong></article>
}

function Panel({ title, subtitle, className = '', children }: { title: string; subtitle?: string; className?: string; children: ReactNode }) {
  return <section className={`panel ${className}`.trim()}><header className="panel-head"><div className="panel-title-wrap"><span className="panel-orb" /><div><h2>{title}</h2>{subtitle ? <p>{subtitle}</p> : null}</div></div></header>{children}</section>
}

function HelpDock({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button type="button" className={compact ? 'help-fab compact' : 'help-fab'} onClick={() => setOpen(true)} aria-label="Abrir ayuda">
        <span className="help-fab-mark">?</span>
        {compact ? null : <span>Ayuda</span>}
      </button>
      {open ? (
        <div className="help-backdrop" role="dialog" aria-modal="true" aria-label="Centro de ayuda" onClick={() => setOpen(false)}>
          <section className="help-card" onClick={(event) => event.stopPropagation()}>
            <header className="help-head">
              <div className="help-brand-lockup">
                <BrandLogo markOnly className="help-brand-mark" />
                <div>
                  <p className="eyebrow">Centro de ayuda</p>
                  <h2>Gride Ledger</h2>
                </div>
              </div>
              <button type="button" className="ghost" onClick={() => setOpen(false)}>Cerrar</button>
            </header>
            <div className="help-grid">
              {helpSections.map((section) => (
                <article key={section.title} className="help-section">
                  <strong>{section.title}</strong>
                  <ul>
                    {section.items.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </>
  )
}

function DashboardTab({ data }: { data: BootstrapResponse }) {
  const freeMarginRecommendation = data.dashboard.goals_reserved < data.dashboard.goals_target
    ? 'Aumentar ahorro, inversion o deuda'
    : data.dashboard.pending_obligations_total > 0
      ? 'Cerrar obligaciones pendientes'
      : 'Liberar una parte a uso personal'

  return (
    <>
      <section className="stats-grid stats-grid-4">
        <MetricCard label="Gasto del mes" value={currency(data.dashboard.current_month_expense_total)} />
        <MetricCard label="Meta quincenal" value={currency(data.dashboard.reserve_per_quincena)} />
        <MetricCard label="Ingreso faltante" value={currency(data.dashboard.income_gap)} />
        <MetricCard label="Cobertura" value={`${Math.round(data.dashboard.quincena_coverage * 100)}%`} />
      </section>
      <section className="bottom-grid">
        <Panel title="Pastel de gastos" subtitle="Distribucion mensual.">
          <ExpensePieChart comparisons={data.dashboard.expense_comparisons} />
        </Panel>
        <Panel title="Buckets del mes" subtitle="Reservas vs objetivo.">
          <div className="progress-stack">
            {data.dashboard.bucket_overviews.map((bucket) => {
              const ratio = bucket.total === 0 ? 0 : Math.min(bucket.reserved / bucket.total, 1)
              return (
                <div key={bucket.label} className="progress-card">
                  <div className="progress-head"><strong>{bucket.label}</strong><span>{Math.round(ratio * 100)}%</span></div>
                  <div className="progress-bar"><div style={{ width: `${ratio * 100}%` }} /></div>
                  <small>{currency(bucket.reserved)} de {currency(bucket.total)}</small>
                </div>
              )
            })}
          </div>
        </Panel>
      </section>
      <section className="bottom-grid">
        <Panel title="Margen libre" subtitle="Excedente del mes.">
          <div className="free-margin-grid">
            <div className="free-margin-card">
              <span className="metric-kicker">Margen estructural</span>
              <strong>{currency(data.dashboard.free_margin_target)}</strong>
            </div>
            <div className="free-margin-card emphasis">
              <span className="metric-kicker">Disponible hoy</span>
              <strong>{currency(data.dashboard.free_margin_available_now)}</strong>
            </div>
          </div>
        </Panel>
        <Panel title="Decidir excedente" subtitle="Elige destino.">
          <div className="decision-grid">
            <article className="decision-card recommended">
              <span className="metric-kicker">Prioridad sugerida</span>
              <strong>{freeMarginRecommendation}</strong>
            </article>
            <article className="decision-card">
              <strong>Pasar a ahorro o inversion</strong>
            </article>
            <article className="decision-card">
              <strong>Abonar a deuda</strong>
            </article>
            <article className="decision-card">
              <strong>Liberar a personal</strong>
            </article>
          </div>
        </Panel>
      </section>
      <section className="bottom-grid single-wide">
        <Panel title="Insights">
          <div className="insight-grid">
            {data.dashboard.generated_insights.map((insight, index) => {
              const tone = insightTone(insight, index)

              return (
                <article key={insight.title} className={`insight-card insight-${tone.className}`}>
                  <div className="insight-top">
                    <span className={`insight-badge ${tone.className}`}>{tone.label}</span>
                    <strong>{insight.title}</strong>
                  </div>
                  <p>{compactInsightBody(insight.body)}</p>
                </article>
              )
            })}
          </div>
        </Panel>
      </section>
      {data.dashboard.credit_card_alerts.length > 0 ? (
        <section className="bottom-grid single-wide">
          <Panel title="Alertas de tarjetas" subtitle="Seguimiento de fechas limite cercanas.">
            <div className="insight-grid">
              {data.dashboard.credit_card_alerts.map((alert) => (
                <article key={alert.statement_id} className={`insight-card insight-${alert.severity === 'danger' ? 'warning' : alert.severity === 'warning' ? 'neutral' : 'calm'}`}>
                  <div className="insight-top">
                    <span className={`insight-badge ${alert.severity === 'danger' ? 'warning' : alert.severity === 'warning' ? 'neutral' : 'calm'}`}>TC {alert.card_last4}</span>
                    <strong>{alert.title}</strong>
                  </div>
                  <p>{alert.detail}</p>
                </article>
              ))}
            </div>
          </Panel>
        </section>
      ) : null}
    </>
  )
}

function TransactionsTab({
  data,
  canEditData,
  saving,
  editingTransactionId,
  transactionForm,
  setTransactionForm,
  transactionSettlementMode,
  setTransactionSettlementMode,
  categoriesForTransactionKind,
  suggestion,
  onSubmit,
  onEdit,
  onDelete,
  onCancelEdit,
  tagCommandInput,
  setTagCommandInput,
  saveAsCommandTag,
  setSaveAsCommandTag,
  onApplyCommandTag,
}: {
  data: BootstrapResponse
  canEditData: boolean
  saving: boolean
  editingTransactionId: number | null
  transactionForm: TransactionInput
  setTransactionForm: Dispatch<SetStateAction<TransactionInput>>
  transactionSettlementMode: LinkedSettlementMode
  setTransactionSettlementMode: Dispatch<SetStateAction<LinkedSettlementMode>>
  categoriesForTransactionKind: CategoryConfig[]
  suggestion: AllocationSuggestion | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onEdit: (transaction: Transaction) => void
  onDelete: (id: number) => Promise<void>
  onCancelEdit: () => void
  tagCommandInput: string
  setTagCommandInput: Dispatch<SetStateAction<string>>
  saveAsCommandTag: boolean
  setSaveAsCommandTag: Dispatch<SetStateAction<boolean>>
  onApplyCommandTag: (tag: TagConfig) => void
}) {
  const [historyTagFilter, setHistoryTagFilter] = useState('')
  const tagsByLabel = new Map(data.tags.map((tag) => [tag.label, tag]))
  const activeTags = data.tags.filter((tag) => tag.active)
  const linkedIncomeOptions = data.fixed_income_sources.filter((item) => item.active)
  const linkedObligationOptions = data.obligations
  const linkedCreditCardStatements = data.credit_card_statements.filter((item) => item.remaining_amount > 0 || item.id === transactionForm.credit_card_statement_id)
  const selectedFixedIncome = linkedIncomeOptions.find((item) => item.id === transactionForm.fixed_income_source_id) ?? null
  const selectedObligation = linkedObligationOptions.find((item) => item.id === transactionForm.obligation_id) ?? null
  const selectedCreditCardStatement = linkedCreditCardStatements.find((item) => item.id === transactionForm.credit_card_statement_id) ?? null
  const selectedLinkedBalance = transactionForm.kind === 'ingreso'
    ? selectedFixedIncome?.current_period_balance ?? 0
    : transactionForm.kind === 'gasto'
      ? selectedCreditCardStatement?.remaining_amount ?? selectedObligation?.current_period_balance ?? 0
      : 0
  const filteredTransactions = historyTagFilter
    ? data.transactions.filter((transaction) => transaction.tags.some((label) => sameTagLabel(label, historyTagFilter)))
    : data.transactions
  const filteredHistoryTotal = filteredTransactions.reduce((sum, transaction) => sum + transaction.amount, 0)
  const matchedCommandTag = findTagByLabel(data.tags, tagCommandInput)

  return (
    <section className="content-grid single-focus">
      {!canEditData ? <div className="banner">Tu perfil es de consulta. Puedes revisar el historial, pero no registrar ni editar movimientos.</div> : null}
      <Panel title={editingTransactionId ? 'Editar movimiento' : 'Registrar movimiento'} className={`transaction-panel kind-${transactionForm.kind}`}>
        <div className={`form-live-banner kind-${transactionForm.kind}`}>
          <div>
            <strong>{transactionKindLabels[transactionForm.kind]} · {currency(transactionForm.amount || 0)}</strong>
            <p>{editingTransactionId ? 'Modo edicion activo.' : 'Nuevo registro en curso.'}</p>
          </div>
          <small>{transactionForm.wallet || 'Banco'} · {transactionForm.category || 'Categoria pendiente'}</small>
        </div>
        <form className="form-grid dynamic-form" onSubmit={onSubmit}>
          <label className="span-2">
            Tag rapido
            <input
              list="transaction-tag-options"
              value={tagCommandInput}
              placeholder="#limpieza o #pedidosya"
              onChange={(event) => {
                const nextValue = event.target.value
                setTagCommandInput(nextValue)
                const matchedTag = findTagByLabel(data.tags, nextValue)
                if (!matchedTag) {
                  return
                }

                setTransactionForm((current) => ({
                  ...current,
                  tags: current.tags.some((item) => sameTagLabel(item, matchedTag.label)) ? current.tags : [...current.tags, matchedTag.label],
                }))

                if (matchedTag.command_enabled) {
                  onApplyCommandTag(matchedTag)
                }
              }}
            />
            <datalist id="transaction-tag-options">
              {activeTags.map((tag) => <option key={tag.id} value={`#${tag.label}`} />)}
            </datalist>
          </label>
          <label className="span-2 checkbox-row tag-command-toggle">
            <input type="checkbox" checked={saveAsCommandTag} onChange={(event) => setSaveAsCommandTag(event.target.checked)} /> Guardar este movimiento como tag comando
          </label>
          {matchedCommandTag?.command_enabled ? <div className="span-2 banner subtle">Preset listo: #{matchedCommandTag.label}</div> : null}
          <div className="span-2 tag-wrap tag-wrap-top">
            {activeTags.map((tag) => {
              const selected = transactionForm.tags.some((item) => sameTagLabel(item, tag.label))
              return (
                <button
                  key={tag.id}
                  type="button"
                  className={selected ? 'tag active' : 'tag'}
                  onClick={() => {
                    if (selected) {
                      setTransactionForm((current) => ({ ...current, tags: current.tags.filter((item) => !sameTagLabel(item, tag.label)) }))
                      if (sameTagLabel(tagCommandInput, tag.label)) {
                        setTagCommandInput('')
                      }
                      return
                    }

                    setTagCommandInput(`#${tag.label}`)
                    setTransactionForm((current) => ({ ...current, tags: [...current.tags, tag.label] }))
                    if (tag.command_enabled) {
                      onApplyCommandTag(tag)
                    }
                  }}
                >
                  #{tag.label}
                </button>
              )
            })}
          </div>
          <div className="span-2 form-kind-block">
            <small>Tipo de movimiento</small>
            <div className="kind-chip-row">
              {(Object.keys(transactionKindLabels) as TransactionKind[]).map((kind) => (
                <button key={kind} type="button" className={transactionForm.kind === kind ? 'kind-chip active' : 'kind-chip'} onClick={() => {
                  setTransactionSettlementMode('partial')
                  setTransactionForm((current) => ({ ...current, kind, category: '', amount: 0, fixed_income_source_id: null, obligation_id: null, credit_card_statement_id: null }))
                }}>
                  <strong>{transactionKindLabels[kind]}</strong>
                </button>
              ))}
            </div>
          </div>
          {transactionForm.kind === 'ingreso' ? (
            <>
              <label>
                Ingreso fijo vinculado
                <select value={transactionForm.fixed_income_source_id ?? ''} onChange={(event) => {
                  const nextId = event.target.value ? Number(event.target.value) : null
                  const linkedItem = linkedIncomeOptions.find((item) => item.id === nextId) ?? null
                  setTransactionForm((current) => ({
                    ...current,
                    fixed_income_source_id: nextId,
                    obligation_id: null,
                    credit_card_statement_id: null,
                    wallet: linkedItem?.wallet ?? current.wallet,
                    category: linkedItem?.label ?? current.category,
                    amount: transactionSettlementMode === 'complete' && linkedItem ? linkedItem.current_period_balance : current.amount,
                  }))
                }}>
                  <option value="">Sin vincular</option>
                  {linkedIncomeOptions.map((item) => <option key={item.id} value={item.id}>{`${item.label} · pendiente ${currency(item.current_period_balance)}`}</option>)}
                </select>
              </label>
              <div className="span-2 form-kind-block">
                <small>Aplicacion del ingreso</small>
                <div className="settlement-mode-row">
                  <button type="button" className={transactionSettlementMode === 'partial' ? 'tag active' : 'tag'} onClick={() => setTransactionSettlementMode('partial')}>Parcial</button>
                  <button type="button" className={transactionSettlementMode === 'complete' ? 'tag active' : 'tag'} onClick={() => {
                    setTransactionSettlementMode('complete')
                    if (selectedFixedIncome) {
                      setTransactionForm((current) => ({ ...current, amount: selectedFixedIncome.current_period_balance }))
                    }
                  }}>Completo</button>
                </div>
              </div>
              {selectedFixedIncome ? <div className="span-2 banner subtle">Registrado este mes: {currency(selectedFixedIncome.current_period_recorded_amount)} · Pendiente: {currency(selectedFixedIncome.current_period_balance)} de {currency(selectedFixedIncome.current_period_expected_amount)}.</div> : null}
            </>
          ) : null}
          {transactionForm.kind === 'gasto' ? (
            <>
              <label>
                Pago de tarjeta vinculado
                <select value={transactionForm.credit_card_statement_id ?? ''} onChange={(event) => {
                  const nextId = event.target.value ? Number(event.target.value) : null
                  const linkedStatement = linkedCreditCardStatements.find((item) => item.id === nextId) ?? null
                  setTransactionForm((current) => ({
                    ...current,
                    credit_card_statement_id: nextId,
                    obligation_id: null,
                    fixed_income_source_id: null,
                    category: linkedStatement ? `Pago TC ${linkedStatement.card_last4}` : current.category,
                    amount: transactionSettlementMode === 'complete' && linkedStatement ? linkedStatement.remaining_amount : current.amount,
                  }))
                }}>
                  <option value="">Sin vincular</option>
                  {linkedCreditCardStatements.map((item) => <option key={item.id} value={item.id}>{`${item.card_label} ${item.card_last4} · pendiente ${currency(item.remaining_amount)}`}</option>)}
                </select>
              </label>
              {selectedCreditCardStatement ? (
                <>
                  <div className="span-2 form-kind-block">
                    <small>Aplicacion del pago de tarjeta</small>
                    <div className="settlement-mode-row">
                      <button type="button" className={transactionSettlementMode === 'partial' ? 'tag active' : 'tag'} onClick={() => setTransactionSettlementMode('partial')}>Parcial</button>
                      <button type="button" className={transactionSettlementMode === 'complete' ? 'tag active' : 'tag'} onClick={() => {
                        setTransactionSettlementMode('complete')
                        setTransactionForm((current) => ({ ...current, amount: selectedCreditCardStatement.remaining_amount }))
                      }}>Completo</button>
                    </div>
                  </div>
                  <div className="span-2 banner subtle">Estado {selectedCreditCardStatement.card_last4}: {currency(selectedCreditCardStatement.statement_amount)} · fijo conciliado {currency(selectedCreditCardStatement.fixed_items_total)} · pendiente {currency(selectedCreditCardStatement.remaining_amount)}.</div>
                </>
              ) : null}
              {!selectedCreditCardStatement ? (
                <>
                  <label>
                    Gasto fijo vinculado
                    <select value={transactionForm.obligation_id ?? ''} onChange={(event) => {
                      const nextId = event.target.value ? Number(event.target.value) : null
                      const linkedItem = linkedObligationOptions.find((item) => item.id === nextId) ?? null
                      setTransactionForm((current) => ({
                        ...current,
                        obligation_id: nextId,
                        fixed_income_source_id: null,
                        credit_card_statement_id: null,
                        category: linkedItem ? categoryLabelById(data.categories, linkedItem.category_id) || current.category : current.category,
                        amount: transactionSettlementMode === 'complete' && linkedItem ? linkedItem.current_period_balance : current.amount,
                      }))
                    }}>
                      <option value="">Sin vincular</option>
                      {linkedObligationOptions.map((item) => <option key={item.id} value={item.id}>{`${item.label} · pendiente ${currency(item.current_period_balance)}`}</option>)}
                    </select>
                  </label>
                  <div className="span-2 form-kind-block">
                    <small>Aplicacion del gasto</small>
                    <div className="settlement-mode-row">
                      <button type="button" className={transactionSettlementMode === 'partial' ? 'tag active' : 'tag'} onClick={() => setTransactionSettlementMode('partial')}>Parcial</button>
                      <button type="button" className={transactionSettlementMode === 'complete' ? 'tag active' : 'tag'} onClick={() => {
                        setTransactionSettlementMode('complete')
                        if (selectedObligation) {
                          setTransactionForm((current) => ({ ...current, amount: selectedObligation.current_period_balance }))
                        }
                      }}>Completo</button>
                    </div>
                  </div>
                  {selectedObligation ? <div className="span-2 banner subtle">Estado del periodo: {selectedObligation.current_period_status}. Registrado: {currency(selectedObligation.current_period_recorded_amount)} · Pendiente: {currency(selectedObligation.current_period_balance)} de {currency(selectedObligation.current_period_expected_amount)}.</div> : null}
                </>
              ) : null}
            </>
          ) : null}
          <label>
            Monto
            <input type="number" min="0" step="0.01" value={transactionForm.amount || ''} onChange={(event) => setTransactionForm((current) => ({ ...current, amount: Number(event.target.value) }))} />
          </label>
          <label>
            Cartera
            <select value={transactionForm.wallet} onChange={(event) => setTransactionForm((current) => ({ ...current, wallet: event.target.value }))}>
              {data.wallets.map((wallet) => <option key={wallet} value={wallet}>{wallet}</option>)}
            </select>
          </label>
          <label>
            Categoria
            <select value={transactionForm.category} onChange={(event) => setTransactionForm((current) => ({ ...current, category: event.target.value }))}>
              <option value="">Selecciona una categoria</option>
              {categoriesForTransactionKind.map((category) => <option key={category.id} value={category.label}>{category.label}</option>)}
            </select>
          </label>
          <label>
            Fecha
            <input type="datetime-local" value={transactionForm.date} onChange={(event) => setTransactionForm((current) => ({ ...current, date: event.target.value }))} />
          </label>
          <label className="span-2">
            Notas
            <textarea rows={3} value={transactionForm.notes} onChange={(event) => setTransactionForm((current) => ({ ...current, notes: event.target.value }))} />
          </label>
          <label className="span-2 checkbox-row">
            <input type="checkbox" checked={transactionForm.recurring} onChange={(event) => setTransactionForm((current) => ({ ...current, recurring: event.target.checked }))} />
            Recurrente
          </label>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving || !canEditData || (transactionSettlementMode === 'complete' && !!(transactionForm.fixed_income_source_id || transactionForm.obligation_id) && selectedLinkedBalance <= 0)}>{editingTransactionId ? 'Guardar cambios' : 'Registrar movimiento'}</button>
            {editingTransactionId ? <button type="button" className="ghost" onClick={onCancelEdit}>Cancelar</button> : null}
          </div>
        </form>
        {transactionForm.kind === 'ingreso' && suggestion ? (
          <div className="suggestion-card">
            <h3>Sugerencia</h3>
            <div className="suggestion-grid">
              <span>Obligaciones</span><strong>{currency(suggestion.for_obligations)}</strong>
              <span>Metas</span><strong>{currency(suggestion.for_goals)}</strong>
              <span>Disponible personal</span><strong>{currency(suggestion.for_personal)}</strong>
            </div>
          </div>
        ) : null}
      </Panel>
      <Panel title="Historial">
        <div className="history-toolbar">
          <div className="tag-wrap">
            <button type="button" className={historyTagFilter ? 'tag' : 'tag active'} onClick={() => setHistoryTagFilter('')}>Todos</button>
            {activeTags.map((tag) => (
              <button key={tag.id} type="button" className={sameTagLabel(historyTagFilter, tag.label) ? 'tag active' : 'tag'} onClick={() => setHistoryTagFilter((current) => sameTagLabel(current, tag.label) ? '' : tag.label)}>
                #{tag.label}
              </button>
            ))}
          </div>
          {historyTagFilter ? <div className="history-summary">#{historyTagFilter} · {filteredTransactions.length} mov. · {currency(filteredHistoryTotal)}</div> : null}
        </div>
        <div className="list-stack">
          {filteredTransactions.map((transaction) => (
            <article key={transaction.id} className="list-card" >
              <div className="list-leading list-leading-top">
                {(() => {
                  const category = findCategoryByLabel(data.categories, transaction.category, transaction.kind === 'ingreso' ? 'income' : 'expense')
                  const fallbackColor = transaction.kind === 'ingreso' ? 'emerald' : transaction.kind === 'transferencia' ? 'sky' : 'terracotta'
                  const fallbackIcon = transaction.kind === 'ingreso' ? 'paid' : transaction.kind === 'transferencia' ? 'account_balance' : transaction.kind === 'ahorro' ? 'savings' : transaction.kind === 'inversion' ? 'trending' : 'receipt'
                  return <VisualBadge iconToken={category?.icon_token ?? fallbackIcon} colorToken={category?.color_token ?? fallbackColor} />
                })()}
                <div>
                  <strong>{transaction.category}</strong>
                  <p>{transaction.kind} · {transaction.wallet} · {new Date(transaction.date).toLocaleString()}</p>
                  {transaction.fixed_income_source_id || transaction.obligation_id ? <small>{transaction.fixed_income_source_id ? 'Vinculado a ingreso fijo' : 'Vinculado a gasto fijo'}</small> : null}
                  {transaction.tags.length > 0 ? (
                    <div className="history-tag-row">
                      {transaction.tags.map((label) => {
                        const tag = tagsByLabel.get(label)
                        return <TagPill key={label} label={label} colorToken={tag?.color_token ?? 'sage'} />
                      })}
                    </div>
                  ) : null}
                </div>
                {transaction.notes ? <small>{transaction.notes}</small> : null}
              </div>
              <div className="list-actions">
                <span className={transaction.kind === 'ingreso' ? 'amount positive' : 'amount negative'}>{currency(transaction.amount)}</span>
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => onEdit(transaction)}>Editar</button>
                <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => void onDelete(transaction.id)}>Borrar</button>
              </div>
            </article>
          ))}
          {filteredTransactions.length === 0 ? <div className="banner">No hay movimientos para el tag seleccionado.</div> : null}
        </div>
      </Panel>
    </section>
  )
}

function BaseTab({
  data,
  canEditData,
  saving,
  fixedIncomeForm,
  setFixedIncomeForm,
  obligationForm,
  setObligationForm,
  creditCardForm,
  setCreditCardForm,
  creditCardStatementForm,
  setCreditCardStatementForm,
  editingFixedIncomeId,
  editingObligationId,
  editingCreditCardId,
  editingCreditCardStatementId,
  expenseCategories,
  onFixedIncomeSubmit,
  onObligationSubmit,
  onCreditCardSubmit,
  onCreditCardStatementSubmit,
  onEditFixedIncome,
  onEditObligation,
  onEditCreditCard,
  onEditCreditCardStatement,
  onDeleteFixedIncome,
  onDeleteObligation,
  onDeleteCreditCard,
  onDeleteCreditCardStatement,
}: {
  data: BootstrapResponse
  canEditData: boolean
  saving: boolean
  fixedIncomeForm: FixedIncomeSourceInput
  setFixedIncomeForm: Dispatch<SetStateAction<FixedIncomeSourceInput>>
  obligationForm: ObligationInput
  setObligationForm: Dispatch<SetStateAction<ObligationInput>>
  creditCardForm: CreditCardInput
  setCreditCardForm: Dispatch<SetStateAction<CreditCardInput>>
  creditCardStatementForm: CreditCardStatementInput
  setCreditCardStatementForm: Dispatch<SetStateAction<CreditCardStatementInput>>
  editingFixedIncomeId: number | null
  editingObligationId: number | null
  editingCreditCardId: number | null
  editingCreditCardStatementId: number | null
  expenseCategories: CategoryConfig[]
  onFixedIncomeSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onObligationSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onCreditCardSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onCreditCardStatementSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onEditFixedIncome: (item: FixedIncomeSource) => void
  onEditObligation: (item: Obligation) => void
  onEditCreditCard: (item: CreditCard) => void
  onEditCreditCardStatement: (item: CreditCardStatement) => void
  onDeleteFixedIncome: (id: number) => Promise<void>
  onDeleteObligation: (id: number) => Promise<void>
  onDeleteCreditCard: (id: number) => Promise<void>
  onDeleteCreditCardStatement: (id: number) => Promise<void>
}) {
  const incomeWallets = new Map(data.wallets.map((wallet) => [wallet, walletVisual(wallet)]))
  const selectedStatementCard = data.credit_cards.find((item) => item.id === creditCardStatementForm.credit_card_id) ?? null
  const cardBoundObligations = selectedStatementCard ? data.obligations.filter((item) => item.credit_card_id === selectedStatementCard.id) : []

  return (
    <section className="content-grid">
      {!canEditData ? <div className="banner">Tu perfil es de consulta. La base financiera queda bloqueada para cambios.</div> : null}
      <Panel title="Ingresos fijos" subtitle="Base mensual.">
        <form className="form-grid dynamic-form compact" onSubmit={onFixedIncomeSubmit}>
          <label>
            Etiqueta
            <input value={fixedIncomeForm.label} onChange={(event) => setFixedIncomeForm((current) => ({ ...current, label: event.target.value }))} />
          </label>
          <label>
            Monto
            <input type="number" min="0" step="0.01" value={fixedIncomeForm.amount || ''} onChange={(event) => setFixedIncomeForm((current) => ({ ...current, amount: Number(event.target.value) }))} />
          </label>
          <label>
            Frecuencia
            <select value={fixedIncomeForm.cadence} onChange={(event) => setFixedIncomeForm((current) => normalizeFixedIncomeCadenceFields({ ...current, cadence: event.target.value as FixedIncomeSourceInput['cadence'] }))}>
              <option value="monthly">Mensual</option>
              <option value="biweekly">Quincenal</option>
              <option value="weekly">Semanal</option>
            </select>
          </label>
          {fixedIncomeForm.cadence === 'monthly' ? (
            <label>
              Dia esperado del mes
              <input type="number" min="1" max="31" value={fixedIncomeForm.expected_day} onChange={(event) => setFixedIncomeForm((current) => ({ ...current, expected_day: clampDayOfMonth(Number(event.target.value)) }))} />
            </label>
          ) : null}
          {fixedIncomeForm.cadence === 'biweekly' ? (
            <label>
              Fechas de pago
              <input value="15 y 30 de cada mes" readOnly />
            </label>
          ) : null}
          {fixedIncomeForm.cadence === 'weekly' ? (
            <label>
              Dia de la semana
              <select value={clampWeekday(fixedIncomeForm.expected_weekday)} onChange={(event) => setFixedIncomeForm((current) => ({ ...current, expected_weekday: clampWeekday(Number(event.target.value)) }))}>
                {Object.entries(weekdayLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          ) : null}
          <label>
            Cartera
            <select value={fixedIncomeForm.wallet} onChange={(event) => setFixedIncomeForm((current) => ({ ...current, wallet: event.target.value }))}>
              {data.wallets.map((wallet) => <option key={wallet} value={wallet}>{wallet}</option>)}
            </select>
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={fixedIncomeForm.active} onChange={(event) => setFixedIncomeForm((current) => ({ ...current, active: event.target.checked }))} /> Activo
          </label>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving || !canEditData}>{editingFixedIncomeId ? 'Actualizar ingreso fijo' : 'Agregar ingreso fijo'}</button>
          </div>
        </form>
        <div className="list-stack">
          {data.fixed_income_sources.map((item) => (
            <article key={item.id} className="list-card">
              <div className="list-leading list-leading-top">
                <VisualBadge iconToken={incomeWallets.get(item.wallet)?.icon ?? 'briefcase'} colorToken={incomeWallets.get(item.wallet)?.color ?? 'sky'} />
                <div>
                  <strong>{item.label}</strong>
                  <p>{cadenceScheduleCopy(item.cadence, item.expected_day, item.expected_weekday)} · {item.wallet}</p>
                </div>
              </div>
              <div className="list-actions">
                <span className="amount positive">{currency(item.amount)}</span>
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => onEditFixedIncome(item)}>Editar</button>
                <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => void onDeleteFixedIncome(item.id)}>Borrar</button>
              </div>
            </article>
          ))}
        </div>
      </Panel>
      <Panel title="Gastos fijos" subtitle="Compromisos recurrentes.">
        <form className="form-grid dynamic-form compact" onSubmit={onObligationSubmit}>
          <label>
            Etiqueta
            <input value={obligationForm.label} onChange={(event) => setObligationForm((current) => ({ ...current, label: event.target.value }))} />
          </label>
          <label>
            Monto
            <input type="number" min="0" step="0.01" value={obligationForm.amount || ''} onChange={(event) => setObligationForm((current) => ({ ...current, amount: Number(event.target.value) }))} />
          </label>
          <label>
            Categoria
            <select value={obligationForm.category_id ?? ''} onChange={(event) => setObligationForm((current) => ({ ...current, category_id: event.target.value }))}>
              {expenseCategories.map((category) => <option key={category.id} value={category.id}>{category.label}</option>)}
            </select>
          </label>
          <label>
            Tarjeta asociada
            <select value={obligationForm.credit_card_id ?? ''} onChange={(event) => setObligationForm((current) => ({ ...current, credit_card_id: event.target.value ? Number(event.target.value) : null }))}>
              <option value="">No aplica</option>
              {data.credit_cards.filter((item) => item.active).map((card) => <option key={card.id} value={card.id}>{`${card.label} · ${card.last4}`}</option>)}
            </select>
          </label>
          <label>
            Frecuencia
            <select value={obligationForm.cadence} onChange={(event) => setObligationForm((current) => normalizeObligationCadenceFields({ ...current, cadence: event.target.value as ObligationInput['cadence'] }))}>
              <option value="monthly">Mensual</option>
              <option value="biweekly">Quincenal</option>
              <option value="weekly">Semanal</option>
            </select>
          </label>
          {obligationForm.cadence === 'monthly' ? (
            <label>
              Dia de vencimiento
              <input type="number" min="1" max="31" value={obligationForm.due_day} onChange={(event) => setObligationForm((current) => ({ ...current, due_day: clampDayOfMonth(Number(event.target.value)) }))} />
            </label>
          ) : null}
          {obligationForm.cadence === 'biweekly' ? (
            <label>
              Fechas de vencimiento
              <input value="15 y 30 de cada mes" readOnly />
            </label>
          ) : null}
          {obligationForm.cadence === 'weekly' ? (
            <label>
              Dia de vencimiento semanal
              <select value={clampWeekday(obligationForm.due_weekday)} onChange={(event) => setObligationForm((current) => ({ ...current, due_weekday: clampWeekday(Number(event.target.value)) }))}>
                {Object.entries(weekdayLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          ) : null}
          <label>
            Estado
            <select value={obligationForm.status} onChange={(event) => setObligationForm((current) => ({ ...current, status: event.target.value }))}>
              <option value="Pendiente">Pendiente</option>
              <option value="Parcial">Parcial</option>
              <option value="Cubierto">Cubierto</option>
            </select>
          </label>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving || !canEditData}>{editingObligationId ? 'Actualizar gasto fijo' : 'Agregar gasto fijo'}</button>
          </div>
        </form>
        <div className="list-stack">
          {data.obligations.map((item) => (
            <article key={item.id} className="list-card">
              <div className="list-leading list-leading-top">
                {(() => {
                  const category = data.categories.find((categoryItem) => categoryItem.id === item.category_id)
                  return <VisualBadge iconToken={category?.icon_token ?? 'receipt'} colorToken={category?.color_token ?? 'gold'} />
                })()}
                <div>
                  <strong>{item.label}</strong>
                  <p>{item.status} · {cadenceScheduleCopy(item.cadence, item.due_day, item.due_weekday)}{item.credit_card_id ? ` · TC ${data.credit_cards.find((card) => card.id === item.credit_card_id)?.last4 ?? ''}` : ''}</p>
                </div>
              </div>
              <div className="list-actions">
                <span className="amount neutral">{currency(item.amount)}</span>
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => onEditObligation(item)}>Editar</button>
                <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => void onDeleteObligation(item.id)}>Borrar</button>
              </div>
            </article>
          ))}
        </div>
      </Panel>
      <Panel title="Tarjetas de credito" subtitle="Corte, limite y fecha de pago.">
        <form className="form-grid dynamic-form compact" onSubmit={onCreditCardSubmit}>
          <label>
            Banco o etiqueta
            <input value={creditCardForm.label} onChange={(event) => setCreditCardForm((current) => ({ ...current, label: event.target.value }))} />
          </label>
          <label>
            Ultimos 4
            <input maxLength={4} value={creditCardForm.last4} onChange={(event) => setCreditCardForm((current) => ({ ...current, last4: event.target.value.replace(/\D/g, '').slice(-4) }))} />
          </label>
          <label>
            Dia de corte
            <input type="number" min="1" max="31" value={creditCardForm.closing_day} onChange={(event) => setCreditCardForm((current) => ({ ...current, closing_day: clampDayOfMonth(Number(event.target.value)) }))} />
          </label>
          <label>
            Dia limite de pago
            <input type="number" min="1" max="31" value={creditCardForm.due_day} onChange={(event) => setCreditCardForm((current) => ({ ...current, due_day: clampDayOfMonth(Number(event.target.value)) }))} />
          </label>
          <label>
            Limite de la tarjeta
            <input type="number" min="0" step="0.01" value={creditCardForm.limit_amount || ''} onChange={(event) => setCreditCardForm((current) => ({ ...current, limit_amount: Number(event.target.value) }))} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={creditCardForm.active} onChange={(event) => setCreditCardForm((current) => ({ ...current, active: event.target.checked }))} /> Activa
          </label>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving || !canEditData}>{editingCreditCardId ? 'Actualizar tarjeta' : 'Agregar tarjeta'}</button>
          </div>
        </form>
        <div className="list-stack">
          {data.credit_cards.map((card) => (
            <article key={card.id} className="list-card">
              <div className="list-leading list-leading-top">
                <VisualBadge iconToken="credit_card" colorToken="petrol" />
                <div>
                  <strong>{card.label} · {card.last4}</strong>
                  <p>Corte {card.closing_day} · Pago {card.due_day} · Limite {currency(card.limit_amount)}</p>
                </div>
              </div>
              <div className="list-actions">
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => onEditCreditCard(card)}>Editar</button>
                <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => void onDeleteCreditCard(card.id)}>Borrar</button>
              </div>
            </article>
          ))}
        </div>
      </Panel>
      <Panel title="Estados de cuenta" subtitle="Concilia lo fijo del ciclo antes de pagar la tarjeta.">
        <form className="form-grid dynamic-form compact" onSubmit={onCreditCardStatementSubmit}>
          <label>
            Tarjeta
            <select value={creditCardStatementForm.credit_card_id ?? ''} onChange={(event) => {
              const nextId = event.target.value ? Number(event.target.value) : null
              const nextCard = data.credit_cards.find((item) => item.id === nextId) ?? null
              setCreditCardStatementForm((current) => ({
                ...current,
                credit_card_id: nextId,
                due_date: nextCard ? cardCycleDueDate(current.statement_date, nextCard.due_day) : current.due_date,
                items: nextCard ? data.obligations.filter((item) => item.credit_card_id === nextCard.id).map((item) => ({ obligation_id: item.id, amount: item.amount })) : [],
              }))
            }}>
              <option value="">Selecciona una tarjeta</option>
              {data.credit_cards.filter((item) => item.active).map((card) => <option key={card.id} value={card.id}>{`${card.label} · ${card.last4}`}</option>)}
            </select>
          </label>
          <label>
            Fecha del estado
            <input type="date" value={creditCardStatementForm.statement_date} onChange={(event) => setCreditCardStatementForm((current) => ({ ...current, statement_date: event.target.value, due_date: selectedStatementCard ? cardCycleDueDate(event.target.value, selectedStatementCard.due_day) : current.due_date }))} />
          </label>
          <label>
            Fecha limite de pago
            <input type="date" value={creditCardStatementForm.due_date} onChange={(event) => setCreditCardStatementForm((current) => ({ ...current, due_date: event.target.value }))} />
          </label>
          <label>
            Ano que cubre
            <input type="number" min="2000" max="2100" value={creditCardStatementForm.period_year} onChange={(event) => setCreditCardStatementForm((current) => ({ ...current, period_year: Number(event.target.value) }))} />
          </label>
          <label>
            Mes que cubre
            <select value={creditCardStatementForm.period_month} onChange={(event) => setCreditCardStatementForm((current) => ({ ...current, period_month: Number(event.target.value) }))}>
              {Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}
            </select>
          </label>
          <label>
            Monto del estado
            <input type="number" min="0" step="0.01" value={creditCardStatementForm.statement_amount || ''} onChange={(event) => setCreditCardStatementForm((current) => ({ ...current, statement_amount: Number(event.target.value) }))} />
          </label>
          <label className="span-2">
            Notas
            <textarea rows={2} value={creditCardStatementForm.notes} onChange={(event) => setCreditCardStatementForm((current) => ({ ...current, notes: event.target.value }))} />
          </label>
          <div className="span-2 statement-items-grid">
            {cardBoundObligations.map((item) => {
              const currentItem = creditCardStatementForm.items.find((statementItem) => statementItem.obligation_id === item.id)
              const selected = Boolean(currentItem)
              return (
                <label key={item.id} className="statement-item-card">
                  <span className="checkbox-row">
                    <input type="checkbox" checked={selected} onChange={(event) => setCreditCardStatementForm((current) => ({
                      ...current,
                      items: event.target.checked
                        ? [...current.items.filter((statementItem) => statementItem.obligation_id !== item.id), { obligation_id: item.id, amount: item.amount }]
                        : current.items.filter((statementItem) => statementItem.obligation_id !== item.id),
                    }))} />
                    {item.label}
                  </span>
                  {selected ? <input type="number" min="0" step="0.01" value={currentItem?.amount ?? item.amount} onChange={(event) => setCreditCardStatementForm((current) => ({
                    ...current,
                    items: current.items.map((statementItem) => statementItem.obligation_id === item.id ? { ...statementItem, amount: Number(event.target.value) } : statementItem),
                  }))} /> : null}
                </label>
              )
            })}
            {selectedStatementCard && cardBoundObligations.length === 0 ? <div className="banner">No hay gastos fijos asociados a esta tarjeta todavia.</div> : null}
          </div>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving || !canEditData}>{editingCreditCardStatementId ? 'Actualizar estado' : 'Registrar estado'}</button>
          </div>
        </form>
        <div className="list-stack">
          {data.credit_card_statements.map((statement) => (
            <article key={statement.id} className="list-card">
              <div className="list-leading list-leading-top">
                <VisualBadge iconToken="credit_card" colorToken="petrol" />
                <div>
                  <strong>{statement.card_label} · {statement.card_last4}</strong>
                  <p>Estado {currency(statement.statement_amount)} · vence {statement.due_date.slice(0, 10)} · cubre {statement.period_month}/{statement.period_year}</p>
                  <small>Fijo conciliado {currency(statement.fixed_items_total)} · pagado {currency(statement.paid_amount)} · restante {currency(statement.remaining_amount)}</small>
                </div>
              </div>
              <div className="list-actions">
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => onEditCreditCardStatement(statement)}>Editar</button>
                <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => void onDeleteCreditCardStatement(statement.id)}>Borrar</button>
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </section>
  )
}

function SettingsTab({
  data,
  canEditData,
  saving,
  importing,
  selectedTheme,
  onThemeSelect,
  passwordForm,
  setPasswordForm,
  categoryForm,
  setCategoryForm,
  tagForm,
  setTagForm,
  editingCategoryId,
  editingTagId,
  importResult,
  onPasswordSubmit,
  onLogout,
  onCategorySubmit,
  onTagSubmit,
  onEditCategory,
  onEditTag,
  onToggleCategory,
  onToggleTag,
  onDeleteCategory,
  onDeleteTag,
  onImportFileChange,
  onImport,
  onReset,
  resetCategoryForm,
  resetTagForm,
}: {
  data: BootstrapResponse
  canEditData: boolean
  saving: boolean
  importing: boolean
  selectedTheme: string
  onThemeSelect: (themeId: string) => Promise<void>
  passwordForm: { currentPassword: string; newPassword: string }
  setPasswordForm: Dispatch<SetStateAction<{ currentPassword: string; newPassword: string }>>
  categoryForm: CategoryConfigInput
  setCategoryForm: Dispatch<SetStateAction<CategoryConfigInput>>
  tagForm: TagConfigInput
  setTagForm: Dispatch<SetStateAction<TagConfigInput>>
  editingCategoryId: string | null
  editingTagId: string | null
  importResult: FlutterImportSummary | null
  onPasswordSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onLogout: () => void
  onCategorySubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onTagSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onEditCategory: (category: CategoryConfig) => void
  onEditTag: (tag: TagConfig) => void
  onToggleCategory: (category: CategoryConfig) => Promise<void>
  onToggleTag: (tag: TagConfig) => Promise<void>
  onDeleteCategory: (category: CategoryConfig) => Promise<void>
  onDeleteTag: (tag: TagConfig) => Promise<void>
  onImportFileChange: (file: File | null) => void
  onImport: () => void
  onReset: () => void
  resetCategoryForm: () => void
  resetTagForm: () => void
}) {
  return (
    <section className="settings-grid">
      <Panel title="Paletas">
        <div className="theme-grid">
          {palettes.map((palette) => (
            <button key={palette.id} type="button" className={selectedTheme === palette.id ? 'theme-card active' : 'theme-card'} onClick={() => void onThemeSelect(palette.id)}>
              <div className="theme-swatches">
                <span style={{ background: palette.petrol }} />
                <span style={{ background: palette.gold }} />
                <span style={{ background: palette.sky }} />
                <span style={{ background: palette.terracotta }} />
              </div>
              <strong>{palette.name}</strong>
            </button>
          ))}
        </div>
      </Panel>

      <Panel title="Seguridad" subtitle={`Cuenta activa: ${data.current_username}`}>
        <form className="form-grid dynamic-form compact" onSubmit={onPasswordSubmit}>
          <label>
            Contrasena actual
            <input type="password" value={passwordForm.currentPassword} onChange={(event) => setPasswordForm((current) => ({ ...current, currentPassword: event.target.value }))} />
          </label>
          <label>
            Nueva contrasena
            <input type="password" value={passwordForm.newPassword} onChange={(event) => setPasswordForm((current) => ({ ...current, newPassword: event.target.value }))} />
          </label>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving}>Actualizar contrasena</button>
            <button type="button" className="ghost" onClick={onLogout}>Cerrar sesion en esta PC</button>
          </div>
        </form>
      </Panel>

      <Panel title="Categorias" subtitle="Catalogo editable.">
        {!canEditData ? <p className="read-only-note">Solo lectura para esta cuenta.</p> : null}
        <form className="form-grid dynamic-form compact" onSubmit={onCategorySubmit}>
          <label>
            Nombre
            <input value={categoryForm.label} onChange={(event) => setCategoryForm((current) => ({ ...current, label: event.target.value }))} />
          </label>
          <label>
            Id tecnico
            <input value={categoryForm.id} onChange={(event) => setCategoryForm((current) => ({ ...current, id: slugify(event.target.value) }))} placeholder="Se genera desde el nombre si lo dejas vacio" />
          </label>
          <label>
            Alcance
            <select value={categoryForm.scope} onChange={(event) => setCategoryForm((current) => ({ ...current, scope: event.target.value as CategoryConfig['scope'], type: event.target.value === 'income' ? 'Ingreso' : current.type }))}>
              <option value="expense">Gasto</option>
              <option value="income">Ingreso</option>
            </select>
          </label>
          <label>
            Tipo
            <input value={categoryForm.type} onChange={(event) => setCategoryForm((current) => ({ ...current, type: event.target.value }))} disabled={categoryForm.scope === 'income'} />
          </label>
          <label className="span-2">
            Icono
            <div className="picker-grid icon-picker">
              {iconTokens.map((token) => (
                <button key={token} type="button" className={categoryForm.icon_token === token ? 'picker-chip active' : 'picker-chip'} onClick={() => setCategoryForm((current) => ({ ...current, icon_token: token }))}>
                  <span>{iconGlyph(token)}</span>
                  <small>{iconLabel(token)}</small>
                </button>
              ))}
            </div>
          </label>
          <label className="span-2">
            Color
            <div className="picker-grid color-picker">
              {colorTokens.map((token) => (
                <button key={token} type="button" className={categoryForm.color_token === token ? 'picker-chip active' : 'picker-chip'} onClick={() => setCategoryForm((current) => ({ ...current, color_token: token }))}>
                  <span className="color-dot" style={{ background: tokenColor(token) }} />
                  <small>{token}</small>
                </button>
              ))}
            </div>
          </label>
          <label className="checkbox-row span-2">
            <input type="checkbox" checked={categoryForm.active} onChange={(event) => setCategoryForm((current) => ({ ...current, active: event.target.checked }))} /> Activa
          </label>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving || !canEditData}>{editingCategoryId ? 'Actualizar categoria' : 'Agregar categoria'}</button>
            {editingCategoryId ? <button type="button" className="ghost" onClick={resetCategoryForm}>Cancelar</button> : null}
          </div>
        </form>
        <div className="list-stack">
          {data.categories.map((category) => (
            <article key={category.id} className="list-card">
              <div className="list-leading">
                <span className="icon-badge" style={{ background: `${tokenColor(category.color_token)}22`, color: tokenColor(category.color_token) }}>{iconGlyph(category.icon_token)}</span>
                <div>
                  <strong>{category.label}</strong>
                  <p>{category.scope} · {category.type} · {category.active ? 'activa' : 'oculta'}</p>
                </div>
              </div>
              <div className="list-actions">
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => onEditCategory(category)}>Editar</button>
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => void onToggleCategory(category)}>{category.active ? 'Ocultar' : 'Activar'}</button>
                <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => void onDeleteCategory(category)}>Eliminar</button>
              </div>
            </article>
          ))}
        </div>
      </Panel>

      <Panel title="Tags" subtitle="Etiquetas rapidas.">
        {!canEditData ? <p className="read-only-note">Solo lectura para esta cuenta.</p> : null}
        <form className="form-grid dynamic-form compact" onSubmit={onTagSubmit}>
          <label>
            Nombre
            <input value={tagForm.label} onChange={(event) => setTagForm((current) => ({ ...current, label: event.target.value }))} />
          </label>
          <label>
            Id tecnico
            <input value={tagForm.id} onChange={(event) => setTagForm((current) => ({ ...current, id: slugify(event.target.value) }))} placeholder="Se genera desde el nombre si lo dejas vacio" />
          </label>
          <label className="span-2">
            Color
            <div className="picker-grid color-picker">
              {colorTokens.map((token) => (
                <button key={token} type="button" className={tagForm.color_token === token ? 'picker-chip active' : 'picker-chip'} onClick={() => setTagForm((current) => ({ ...current, color_token: token }))}>
                  <span className="color-dot" style={{ background: tokenColor(token) }} />
                  <small>{token}</small>
                </button>
              ))}
            </div>
          </label>
          <label className="checkbox-row span-2">
            <input type="checkbox" checked={tagForm.active} onChange={(event) => setTagForm((current) => ({ ...current, active: event.target.checked }))} /> Activo
          </label>
          <div className="span-2 action-row">
            <button type="submit" disabled={saving || !canEditData}>{editingTagId ? 'Actualizar tag' : 'Agregar tag'}</button>
            {editingTagId ? <button type="button" className="ghost" onClick={resetTagForm}>Cancelar</button> : null}
          </div>
        </form>
        <div className="list-stack">
          {data.tags.map((tag) => (
            <article key={tag.id} className="list-card">
              <div className="list-leading">
                <span className="icon-badge narrow" style={{ background: `${tokenColor(tag.color_token)}22`, color: tokenColor(tag.color_token) }}>#</span>
                <div>
                  <strong>{tag.label}</strong>
                  <p>{tag.active ? 'activo' : 'oculto'} · {tag.color_token}</p>
                </div>
              </div>
              <div className="list-actions">
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => onEditTag(tag)}>Editar</button>
                <button type="button" className="ghost" disabled={!canEditData} onClick={() => void onToggleTag(tag)}>{tag.active ? 'Ocultar' : 'Activar'}</button>
                <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => void onDeleteTag(tag)}>Eliminar</button>
              </div>
            </article>
          ))}
        </div>
      </Panel>

      <Panel title="Migracion y reset" subtitle="Importacion y reinicio.">
        <div className="column-stack">
          {!canEditData ? <p className="read-only-note">La importacion y el reinicio requieren una cuenta con permiso de edicion.</p> : null}
          <label>
            Archivo SQLite legado
            <input type="file" accept=".db,.sqlite,.sqlite3" onChange={(event) => onImportFileChange(event.target.files?.[0] ?? null)} />
          </label>
          <div className="action-row">
            <button type="button" disabled={importing || !data || !canEditData} onClick={onImport}>{importing ? 'Importando...' : 'Importar base Flutter'}</button>
            <button type="button" disabled={saving || !canEditData} className="ghost danger" onClick={onReset}>Reiniciar configuracion inicial</button>
          </div>
          <p>El importador conserva ingresos fijos, obligaciones, transacciones, categorias y tags del archivo legado.</p>
          {importResult ? <div className="suggestion-card"><p>Importados {importResult.fixed_income_sources} ingresos fijos, {importResult.obligations} obligaciones y {importResult.transactions} movimientos.</p></div> : null}
        </div>
      </Panel>
      <HelpDock />
    </section>
  )
}

function OwnerPanel({
  data,
  saving,
  error,
  userForm,
  setUserForm,
  onUserSubmit,
  onUpdateUserAccess,
  onDeleteUser,
  onLogout,
}: {
  data: OwnerPanelResponse
  saving: boolean
  error: string | null
  userForm: { username: string; password: string; role: UserRole }
  setUserForm: Dispatch<SetStateAction<{ username: string; password: string; role: UserRole }>>
  onUserSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onUpdateUserAccess: (userId: number, role: UserRole, active: boolean) => Promise<void>
  onDeleteUser: (userId: number, username: string) => void
  onLogout: () => void
}) {
  const [auditSearch, setAuditSearch] = useState('')
  const [auditActionFilter, setAuditActionFilter] = useState('all')
  const [auditPage, setAuditPage] = useState(1)
  const auditPageSize = 6
  const auditActionOptions = useMemo(() => Array.from(new Set(data.audit_events.map((item) => item.action))), [data.audit_events])
  const filteredAuditEvents = useMemo(() => {
    const query = auditSearch.trim().toLowerCase()
    return data.audit_events.filter((item) => {
      const matchesAction = auditActionFilter === 'all' || item.action === auditActionFilter
      const haystack = `${item.actor_username} ${item.action} ${item.target_type} ${item.target_value} ${item.detail}`.toLowerCase()
      const matchesQuery = query.length === 0 || haystack.includes(query)
      return matchesAction && matchesQuery
    })
  }, [auditActionFilter, auditSearch, data.audit_events])
  const auditTotalPages = Math.max(1, Math.ceil(filteredAuditEvents.length / auditPageSize))
  const safeAuditPage = Math.min(auditPage, auditTotalPages)
  const pagedAuditEvents = filteredAuditEvents.slice((safeAuditPage - 1) * auditPageSize, safeAuditPage * auditPageSize)

  return (
    <main className="app-shell owner-shell">
      <section className="hero-panel owner-hero-panel">
        <div>
          <BrandLogo className="brand-hero-logo" />
          <h1>Panel owner</h1>
          <div className="hero-meta">
            <span>Control maestro de accesos</span>
            <span>{data.current_username}</span>
          </div>
        </div>
        <div className="hero-card">
          <BrandLogo dark markOnly className="brand-mark brand-mark-on-dark" />
          <span>Ruta separada</span>
          <strong>/owner</strong>
          <p>Desde aqui creas, ajustas, desactivas y eliminas usuarios del producto.</p>
          <div className="action-row top-gap">
            <button type="button" className="ghost light" onClick={onLogout}>Cerrar sesion</button>
          </div>
        </div>
      </section>

      {error ? <div className="banner error">{error}</div> : null}

      <section className="settings-grid owner-panel-grid">
        <Panel title="Usuarios" subtitle="Accesos del equipo.">
          <form className="form-grid dynamic-form compact" onSubmit={onUserSubmit}>
            <label>
              Usuario
              <input value={userForm.username} onChange={(event) => setUserForm((current) => ({ ...current, username: event.target.value }))} minLength={3} />
            </label>
            <label>
              Contrasena temporal
              <input type="password" value={userForm.password} onChange={(event) => setUserForm((current) => ({ ...current, password: event.target.value }))} minLength={4} />
            </label>
            <label>
              Rol
              <select value={userForm.role} onChange={(event) => setUserForm((current) => ({ ...current, role: event.target.value as UserRole }))}>
                <option value="operator">Operador</option>
                <option value="viewer">Consulta</option>
                <option value="admin">Administrador interno</option>
              </select>
            </label>
            <div className="span-2 action-row">
              <button type="submit" disabled={saving || userForm.username.trim().length < 3 || userForm.password.length < 4}>Crear usuario</button>
            </div>
          </form>
          <div className="list-stack">
            {data.users.map((item) => (
              <article key={item.id} className="list-card">
                <div>
                  <strong>{item.username}</strong>
                  <p>{roleLabels[item.role]} · {item.active ? 'activa' : 'desactivada'}{item.created_by_username ? ` · alta por ${item.created_by_username}` : ''}</p>
                </div>
                <div className="list-actions user-access-actions owner-user-actions">
                  <select value={item.role} disabled={saving || item.username === data.current_username} onChange={(event) => void onUpdateUserAccess(item.id, event.target.value as UserRole, item.active)}>
                    <option value="admin">Administrador interno</option>
                    <option value="operator">Operador</option>
                    <option value="viewer">Consulta</option>
                  </select>
                  <button type="button" className={item.active ? 'ghost danger' : 'ghost'} disabled={saving || item.username === data.current_username} onClick={() => void onUpdateUserAccess(item.id, item.role, !item.active)}>
                    {item.active ? 'Desactivar' : 'Activar'}
                  </button>
                  <button type="button" className="ghost danger" disabled={saving || item.username === data.current_username} onClick={() => onDeleteUser(item.id, item.username)}>
                    Eliminar
                  </button>
                </div>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Auditoria" subtitle="Eventos recientes del owner.">
          <div className="audit-toolbar">
            <label>
              Buscar
              <input value={auditSearch} onChange={(event) => { setAuditSearch(event.target.value); setAuditPage(1) }} placeholder="usuario, accion o detalle" />
            </label>
            <label>
              Tipo
              <select value={auditActionFilter} onChange={(event) => { setAuditActionFilter(event.target.value); setAuditPage(1) }}>
                <option value="all">Todos</option>
                {auditActionOptions.map((action) => <option key={action} value={action}>{auditActionLabels[action] ?? action}</option>)}
              </select>
            </label>
          </div>
          <div className="list-stack">
            {pagedAuditEvents.map((eventItem: AuditEvent) => (
              <article key={eventItem.id} className="list-card audit-card">
                <div>
                  <strong>{auditActionLabels[eventItem.action] ?? eventItem.action}</strong>
                  <p>{eventItem.actor_username} · {new Date(eventItem.created_at_iso).toLocaleString()}</p>
                  <small>{eventItem.target_type}: {eventItem.target_value} · {eventItem.detail}</small>
                </div>
              </article>
            ))}
            {pagedAuditEvents.length === 0 ? <div className="banner">No hay eventos que coincidan con el filtro actual.</div> : null}
          </div>
          <div className="audit-footer">
            <small>{filteredAuditEvents.length} evento(s) · pagina {safeAuditPage} de {auditTotalPages}</small>
            <div className="action-row">
              <button type="button" className="ghost" disabled={safeAuditPage <= 1} onClick={() => setAuditPage((current) => Math.max(1, current - 1))}>Anterior</button>
              <button type="button" className="ghost" disabled={safeAuditPage >= auditTotalPages} onClick={() => setAuditPage((current) => Math.min(auditTotalPages, current + 1))}>Siguiente</button>
            </div>
          </div>
        </Panel>
      </section>
    </main>
  )
}

function LoginGate({
  ownerMode = false,
  authStatus,
  error,
  busy,
  onLogin,
}: {
  ownerMode?: boolean
  authStatus: AuthStatus | null
  error: string | null
  busy: boolean
  onLogin: (username: string, password: string, bootstrapCode?: string) => Promise<void>
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [bootstrapCode, setBootstrapCode] = useState('')
  const manualBootstrapEnabled = ownerMode ? Boolean(authStatus?.owner_bootstrap_enabled) : false
  const showBootstrap = ownerMode ? Boolean(authStatus?.admin_bootstrap_required && authStatus?.owner_bootstrap_enabled) : false

  return (
    <main className="login-shell">
      <div className="login-stage" aria-hidden="true">
        <span className="login-orbit orbit-a" />
        <span className="login-orbit orbit-b" />
        <span className="login-orbit orbit-c" />
        <span className="login-grid-line line-a" />
        <span className="login-grid-line line-b" />
      </div>
      <section className="login-card login-card-animated">
        <div className="login-card-inner">
          <div className="login-brand-block">
            <BrandLogo className="brand-login-logo" />
          </div>
          {ownerMode ? <p className="login-bootstrap-copy login-mode-copy">Acceso owner independiente para administracion comercial.</p> : null}
          {ownerMode && authStatus?.owner_bootstrap_warning ? <div className="banner error">{authStatus.owner_bootstrap_warning}</div> : null}
          {error ? <div className="banner error">{error}</div> : null}
          <form className="login-form" onSubmit={(event) => { event.preventDefault(); void onLogin(username, password, bootstrapCode) }}>
            <div className="login-fields">
              <label>
                <span>Usuario</span>
                <input minLength={3} value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Usuario" />
              </label>
              <label>
                <span>{authStatus?.has_users ? 'Contrasena' : 'Contrasena inicial'}</span>
                <input type="password" minLength={4} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Contrasena" />
              </label>
              {showBootstrap ? (
                <label className="login-bootstrap-field">
                  <span>Codigo de bootstrap</span>
                  <input minLength={8} value={bootstrapCode} onChange={(event) => setBootstrapCode(event.target.value)} placeholder="Solo visible en el servidor local" />
                </label>
              ) : null}
            </div>
            {ownerMode && !manualBootstrapEnabled && authStatus?.owner_bootstrap_warning ? <p className="login-bootstrap-copy">La cuenta owner inicial se crea solo desde variables seguras del servidor. El formulario manual no esta disponible en produccion.</p> : null}
            {showBootstrap ? <p className="login-bootstrap-copy">Codigo inicial: {authStatus?.admin_bootstrap_code_path ?? 'admin_bootstrap_code.txt'}</p> : null}
            <div className="action-row login-actions">
              <button type="submit" disabled={busy || username.trim().length < 3 || password.length < 4 || (showBootstrap && bootstrapCode.trim().length < 8)}>{busy ? 'Validando...' : showBootstrap ? ownerMode ? 'Crear acceso owner' : 'Crear acceso admin' : 'Entrar'}</button>
            </div>
          </form>
        </div>
      </section>
    </main>
  )
}

function ExpensePieChart({ comparisons }: { comparisons: BootstrapResponse['dashboard']['expense_comparisons'] }) {
  const items = comparisons.filter((item) => item.current_amount > 0)
  const total = items.reduce((sum, item) => sum + item.current_amount, 0)

  if (total <= 0) {
    return <p>Aun no hay gastos del mes para distribuir en el grafico.</p>
  }

  const radius = 76
  const circumference = 2 * Math.PI * radius
  let offset = 0

  return (
    <div className="pie-layout">
      <svg viewBox="0 0 200 200" className="pie-chart" aria-label="Distribucion de gastos">
        <circle cx="100" cy="100" r={radius} fill="none" stroke="rgba(0,0,0,0.06)" strokeWidth="28" />
        {items.map((item) => {
          const ratio = item.current_amount / total
          const dash = circumference * ratio
          const node = (
            <circle
              key={item.label}
              cx="100"
              cy="100"
              r={radius}
              fill="none"
              stroke={tokenColor(item.color_token)}
              strokeWidth="28"
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 100 100)"
            />
          )
          offset += dash
          return node
        })}
        <text x="100" y="96" textAnchor="middle" className="pie-total-label">Total</text>
        <text x="100" y="118" textAnchor="middle" className="pie-total-value">{currency(total)}</text>
      </svg>
      <div className="pie-legend">
        {items.map((item) => {
          const percentage = Math.round((item.current_amount / total) * 100)
          return (
            <article key={item.label} className="legend-row">
              <span className="icon-badge narrow" style={{ background: `${tokenColor(item.color_token)}22`, color: tokenColor(item.color_token) }}>{iconGlyph(item.icon_token)}</span>
              <div>
                <strong>{item.label}</strong>
                <p>{currency(item.current_amount)} · {percentage}%</p>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}

function SetupWizard({
  wallets,
  expenseCategories,
  canEditData,
  onActivate,
  saving,
  onLogout,
}: {
  wallets: string[]
  expenseCategories: CategoryConfig[]
  canEditData: boolean
  onActivate: (payload: InitialSetupPayload) => Promise<void>
  saving: boolean
  onLogout: () => void
}) {
  const [step, setStep] = useState(0)
  const [fixedIncomes, setFixedIncomes] = useState<FixedIncomeSourceInput[]>([])
  const [obligations, setObligations] = useState<ObligationInput[]>([])
  const [incomeForm, setIncomeForm] = useState<FixedIncomeSourceInput>(emptyFixedIncome(wallets[0] ?? 'Banco'))
  const [obligationForm, setLocalObligationForm] = useState<ObligationInput>(emptyObligation(expenseCategories[0]?.id ?? 'casa'))
  const [editingIncomeIndex, setEditingIncomeIndex] = useState<number | null>(null)
  const [editingObligationIndex, setEditingObligationIndex] = useState<number | null>(null)

  const incomeBaseTotal = fixedIncomes.filter((item) => item.active).reduce((sum, item) => sum + cadenceExpectedMonthlyAmount(item.amount, item.cadence), 0)
  const obligationsTotal = obligations.reduce((sum, item) => sum + cadenceExpectedMonthlyAmount(item.amount, item.cadence), 0)

  const saveIncome = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const payload = normalizeFixedIncomeCadenceFields(incomeForm)
    setFixedIncomes((current) => {
      const next = [...current]
      if (editingIncomeIndex === null) {
        next.push(payload)
      } else {
        next[editingIncomeIndex] = payload
      }
      return next
    })
    setIncomeForm(emptyFixedIncome(wallets[0] ?? 'Banco'))
    setEditingIncomeIndex(null)
  }

  const saveObligation = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const payload = deriveObligationKind(normalizeObligationCadenceFields(obligationForm), expenseCategories)
    setObligations((current) => {
      const next = [...current]
      if (editingObligationIndex === null) {
        next.push(payload)
      } else {
        next[editingObligationIndex] = payload
      }
      return next
    })
    setLocalObligationForm(emptyObligation(expenseCategories[0]?.id ?? 'casa'))
    setEditingObligationIndex(null)
  }

  return (
    <main className="app-shell wizard-shell">
      <section className="wizard-hero">
        <div>
          <BrandLogo className="brand-hero-logo" />
          <p className="eyebrow">Primera configuracion</p>
          <h1>{step === 0 ? 'Define tus ingresos fijos' : step === 1 ? 'Define tus gastos fijos' : 'Activa tu tablero real'}</h1>
        </div>
        <div className="hero-card compact-card">
          <span>Acceso de esta PC activo</span>
          <strong>{`${step + 1}/3`}</strong>
          <p>Puedes cerrar sesion si prefieres salir antes de terminar el wizard.</p>
          <div className="action-row top-gap">
            <button type="button" className="ghost light" onClick={onLogout}>Cerrar sesion</button>
          </div>
        </div>
        <div className="wizard-summary-grid">
          <MetricCard label="Base ingresos" value={currency(incomeBaseTotal)} />
          <MetricCard label="Gastos fijos" value={currency(obligationsTotal)} />
          <MetricCard label="Paso" value={`${step + 1} de 3`} />
        </div>
      </section>

      {!canEditData ? <div className="banner">Tu cuenta no puede completar ni modificar la configuracion inicial.</div> : null}

      <nav className="tab-rail wizard-steps" aria-label="Pasos del asistente">
        {['Ingresos', 'Compromisos', 'Activacion'].map((label, index) => (
          <button key={label} type="button" className={step === index ? 'tab-chip active' : 'tab-chip'} onClick={() => { if (index === 0 || fixedIncomes.length > 0) setStep(index) }}>
            <strong>{label}</strong>
            <span>{index === 0 ? 'Base esperada' : index === 1 ? 'Mapa fijo' : 'Resumen final'}</span>
          </button>
        ))}
      </nav>

      {step === 0 ? (
        <Panel title="Ingresos fijos" subtitle="Base esperada.">
          <form className="form-grid dynamic-form" onSubmit={saveIncome}>
            <label>
              Etiqueta
              <input value={incomeForm.label} onChange={(event) => setIncomeForm((current) => ({ ...current, label: event.target.value }))} />
            </label>
            <label>
              Monto por pago esperado
              <input type="number" min="0" step="0.01" value={incomeForm.amount || ''} onChange={(event) => setIncomeForm((current) => ({ ...current, amount: Number(event.target.value) }))} />
            </label>
            <label>
              Frecuencia
              <select value={incomeForm.cadence} onChange={(event) => setIncomeForm((current) => normalizeFixedIncomeCadenceFields({ ...current, cadence: event.target.value as FixedIncomeSourceInput['cadence'] }))}>
                <option value="monthly">Mensual</option>
                <option value="biweekly">Quincenal</option>
                <option value="weekly">Semanal</option>
              </select>
            </label>
            {incomeForm.cadence === 'monthly' ? (
              <label>
                Dia esperado del mes
                <input type="number" min="1" max="31" value={incomeForm.expected_day} onChange={(event) => setIncomeForm((current) => ({ ...current, expected_day: clampDayOfMonth(Number(event.target.value)) }))} />
              </label>
            ) : null}
            {incomeForm.cadence === 'biweekly' ? (
              <label>
                Fechas de pago
                <input value="15 y 30 de cada mes" readOnly />
              </label>
            ) : null}
            {incomeForm.cadence === 'weekly' ? (
              <label>
                Dia de la semana
                <select value={clampWeekday(incomeForm.expected_weekday)} onChange={(event) => setIncomeForm((current) => ({ ...current, expected_weekday: clampWeekday(Number(event.target.value)) }))}>
                  {Object.entries(weekdayLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
            ) : null}
            <label>
              Cartera
              <select value={incomeForm.wallet} onChange={(event) => setIncomeForm((current) => ({ ...current, wallet: event.target.value }))}>
                {wallets.map((wallet) => <option key={wallet} value={wallet}>{wallet}</option>)}
              </select>
            </label>
            <label className="checkbox-row">
              <input type="checkbox" checked={incomeForm.active} onChange={(event) => setIncomeForm((current) => ({ ...current, active: event.target.checked }))} /> Activo
            </label>
            <div className="span-2 banner subtle">{cadenceProjectionCopy(incomeForm.amount || 0, incomeForm.cadence, 'pago')}</div>
            <div className="span-2 action-row">
              <button type="submit" disabled={!canEditData}>{editingIncomeIndex === null ? 'Agregar ingreso fijo' : 'Actualizar ingreso fijo'}</button>
            </div>
          </form>
          <div className="list-stack">
            {fixedIncomes.map((item, index) => (
              <article key={`${item.label}-${index}`} className="list-card">
                <div>
                  <strong>{item.label}</strong>
                  <p>{cadenceScheduleCopy(item.cadence, item.expected_day, item.expected_weekday)} · {item.wallet}</p>
                  <small>{cadenceProjectionCopy(item.amount, item.cadence, 'pago')}</small>
                </div>
                <div className="list-actions">
                  <span className="amount positive">{currency(cadenceExpectedMonthlyAmount(item.amount, item.cadence))}</span>
                  <button type="button" className="ghost" disabled={!canEditData} onClick={() => { setEditingIncomeIndex(index); setIncomeForm(normalizeFixedIncomeCadenceFields(item)) }}>Editar</button>
                  <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => setFixedIncomes((current) => current.filter((_, currentIndex) => currentIndex !== index))}>Borrar</button>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      ) : null}

      {step === 1 ? (
        <Panel title="Gastos fijos" subtitle="Compromisos iniciales.">
          <form className="form-grid dynamic-form" onSubmit={saveObligation}>
            <label>
              Etiqueta
              <input value={obligationForm.label} onChange={(event) => setLocalObligationForm((current) => ({ ...current, label: event.target.value }))} />
            </label>
            <label>
              Monto por pago
              <input type="number" min="0" step="0.01" value={obligationForm.amount || ''} onChange={(event) => setLocalObligationForm((current) => ({ ...current, amount: Number(event.target.value) }))} />
            </label>
            <label>
              Categoria
              <select value={obligationForm.category_id ?? ''} onChange={(event) => setLocalObligationForm((current) => ({ ...current, category_id: event.target.value }))}>
                {expenseCategories.map((category) => <option key={category.id} value={category.id}>{category.label}</option>)}
              </select>
            </label>
            <label>
              Frecuencia
              <select value={obligationForm.cadence} onChange={(event) => setLocalObligationForm((current) => normalizeObligationCadenceFields({ ...current, cadence: event.target.value as ObligationInput['cadence'] }))}>
                <option value="monthly">Mensual</option>
                <option value="biweekly">Quincenal</option>
                <option value="weekly">Semanal</option>
              </select>
            </label>
            {obligationForm.cadence === 'monthly' ? (
              <label>
                Dia de vencimiento
                <input type="number" min="1" max="31" value={obligationForm.due_day} onChange={(event) => setLocalObligationForm((current) => ({ ...current, due_day: clampDayOfMonth(Number(event.target.value)) }))} />
              </label>
            ) : null}
            {obligationForm.cadence === 'biweekly' ? (
              <label>
                Fechas de vencimiento
                <input value="15 y 30 de cada mes" readOnly />
              </label>
            ) : null}
            {obligationForm.cadence === 'weekly' ? (
              <label>
                Dia de vencimiento semanal
                <select value={clampWeekday(obligationForm.due_weekday)} onChange={(event) => setLocalObligationForm((current) => ({ ...current, due_weekday: clampWeekday(Number(event.target.value)) }))}>
                  {Object.entries(weekdayLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
            ) : null}
            <label>
              Estado
              <select value={obligationForm.status} onChange={(event) => setLocalObligationForm((current) => ({ ...current, status: event.target.value }))}>
                <option value="Pendiente">Pendiente</option>
                <option value="Parcial">Parcial</option>
                <option value="Cubierto">Cubierto</option>
              </select>
            </label>
            <div className="span-2 banner subtle">{cadenceProjectionCopy(obligationForm.amount || 0, obligationForm.cadence, 'pago')}</div>
            <div className="span-2 action-row">
              <button type="submit" disabled={!canEditData}>{editingObligationIndex === null ? 'Agregar gasto fijo' : 'Actualizar gasto fijo'}</button>
            </div>
          </form>
          <div className="list-stack">
            {obligations.map((item, index) => (
              <article key={`${item.label}-${index}`} className="list-card">
                <div>
                  <strong>{item.label}</strong>
                  <p>{item.status} · {cadenceScheduleCopy(item.cadence, item.due_day, item.due_weekday)}</p>
                  <small>{cadenceProjectionCopy(item.amount, item.cadence, 'pago')}</small>
                </div>
                <div className="list-actions">
                  <span className="amount neutral">{currency(cadenceExpectedMonthlyAmount(item.amount, item.cadence))}</span>
                  <button type="button" className="ghost" disabled={!canEditData} onClick={() => { setEditingObligationIndex(index); setLocalObligationForm(normalizeObligationCadenceFields(item)) }}>Editar</button>
                  <button type="button" className="ghost danger" disabled={!canEditData} onClick={() => setObligations((current) => current.filter((_, currentIndex) => currentIndex !== index))}>Borrar</button>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      ) : null}

      {step === 2 ? (
        <Panel title="Resumen de activacion" subtitle="Confirmacion final.">
          <div className="wizard-summary-stack">
            <div className="summary-line"><span>Ingresos fijos</span><strong>{fixedIncomes.length}</strong></div>
            <div className="summary-line"><span>Base mensual esperada</span><strong>{currency(incomeBaseTotal)}</strong></div>
            <div className="summary-line"><span>Gastos fijos</span><strong>{obligations.length}</strong></div>
            <div className="summary-line"><span>Apartado quincenal base</span><strong>{currency(obligationsTotal / 2)}</strong></div>
          </div>
        </Panel>
      ) : null}

      <div className="wizard-actions">
        {step > 0 ? <button type="button" className="ghost" onClick={() => setStep((current) => current - 1)}>Atras</button> : null}
        {step < 2 ? <button type="button" disabled={(step === 0 && fixedIncomes.length === 0) || !canEditData} onClick={() => setStep((current) => current + 1)}>Continuar</button> : <button type="button" disabled={saving || fixedIncomes.length === 0 || !canEditData} onClick={() => void onActivate({ fixed_income_sources: fixedIncomes, obligations })}>{saving ? 'Guardando...' : 'Activar Gride Ledger'}</button>}
      </div>
      <HelpDock compact />
    </main>
  )
}

export default App
