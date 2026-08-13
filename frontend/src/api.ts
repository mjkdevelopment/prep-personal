import type {
  AllocationSuggestion,
  AuthStatus,
  BootstrapResponse,
  CategoryConfig,
  CategoryConfigInput,
  FixedIncomeSourceInput,
  FlutterImportSummary,
  InitialSetupPayload,
  LoginResponse,
  OwnerPanelResponse,
  ObligationInput,
  TagConfig,
  TagConfigInput,
  TransactionInput,
  UserAccessUpdateInput,
  UserSummary,
} from './types'

const apiBase = '/api'
const sessionStorageKey = 'gride-ledger-session-token'

export function getSessionToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  return window.localStorage.getItem(sessionStorageKey)
}

export function setSessionToken(token: string): void {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(sessionStorageKey, token)
  }
}

export function clearSessionToken(): void {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(sessionStorageKey)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const sessionToken = getSessionToken()
  const headers = new Headers(init?.headers ?? undefined)
  if (!(init?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (sessionToken) {
    headers.set('x-session-token', sessionToken)
  }

  const response = await fetch(`${apiBase}${path}`, {
    headers,
    ...init,
  })

  if (!response.ok) {
    if (response.status === 401) {
      clearSessionToken()
    }
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const fetchAuthStatus = () => request<AuthStatus>('/auth/status')
export async function bootstrapOwner(username: string, password: string, bootstrapCode: string, deviceName: string): Promise<LoginResponse> {
  const response = await request<LoginResponse>('/auth/bootstrap-owner', { method: 'POST', body: JSON.stringify({ username, password, bootstrap_code: bootstrapCode, device_name: deviceName }) })
  setSessionToken(response.session_token)
  return response
}
export async function bootstrapAdmin(username: string, password: string, bootstrapCode: string, deviceName: string): Promise<LoginResponse> {
  const response = await request<LoginResponse>('/auth/bootstrap-admin', { method: 'POST', body: JSON.stringify({ username, password, bootstrap_code: bootstrapCode, device_name: deviceName }) })
  setSessionToken(response.session_token)
  return response
}
export async function login(username: string, password: string, deviceName: string): Promise<LoginResponse> {
  const response = await request<LoginResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password, device_name: deviceName }) })
  setSessionToken(response.session_token)
  return response
}
export async function loginOwner(username: string, password: string, deviceName: string): Promise<LoginResponse> {
  const response = await request<LoginResponse>('/auth/login-owner', { method: 'POST', body: JSON.stringify({ username, password, device_name: deviceName }) })
  setSessionToken(response.session_token)
  return response
}
export const logout = async () => { await request<void>('/auth/logout', { method: 'POST' }); clearSessionToken() }
export const changePassword = (currentPassword: string, newPassword: string) => request<void>('/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) })
export const createUser = (username: string, password: string, role: string) => request<UserSummary>('/users', { method: 'POST', body: JSON.stringify({ username, password, role }) })
export const updateUserAccess = (userId: number, payload: UserAccessUpdateInput) => request<UserSummary>(`/users/${userId}/access`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteUser = (userId: number) => request<void>(`/users/${userId}`, { method: 'DELETE' })
export const fetchBootstrap = () => request<BootstrapResponse>('/bootstrap')
export const fetchOwnerPanel = () => request<OwnerPanelResponse>('/owner/panel')
export const updateThemePreference = (themeId: string) => request<void>('/preferences/theme', { method: 'PUT', body: JSON.stringify({ theme_id: themeId }) })
export const fetchIncomeSuggestion = (amount: number) => request<AllocationSuggestion>(`/suggestions/income?amount=${amount}`)
export const createTransaction = (payload: TransactionInput) => request('/transactions', { method: 'POST', body: JSON.stringify(payload) })
export const updateTransaction = (id: number, payload: TransactionInput) => request(`/transactions/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteTransaction = (id: number) => request(`/transactions/${id}`, { method: 'DELETE' })
export const createFixedIncomeSource = (payload: FixedIncomeSourceInput) => request('/fixed-income-sources', { method: 'POST', body: JSON.stringify(payload) })
export const updateFixedIncomeSource = (id: number, payload: FixedIncomeSourceInput) => request(`/fixed-income-sources/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteFixedIncomeSource = (id: number) => request(`/fixed-income-sources/${id}`, { method: 'DELETE' })
export const createObligation = (payload: ObligationInput) => request('/obligations', { method: 'POST', body: JSON.stringify(payload) })
export const updateObligation = (id: number, payload: ObligationInput) => request(`/obligations/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteObligation = (id: number) => request(`/obligations/${id}`, { method: 'DELETE' })
export const completeInitialSetup = (payload: InitialSetupPayload) => request<BootstrapResponse>('/setup/complete', { method: 'POST', body: JSON.stringify(payload) })
export const resetInitialSetup = () => request<void>('/setup/reset', { method: 'POST' })
export const deleteCategory = (id: string) => request<void>(`/categories/${id}`, { method: 'DELETE' })
export const deleteTag = (id: string) => request<void>(`/tags/${id}`, { method: 'DELETE' })
export const upsertCategory = (payload: CategoryConfigInput) => request<CategoryConfig>(`/categories${payload.id ? `/${payload.id}` : ''}`.replace(/\/$/, ''), { method: payload.id ? 'PUT' : 'POST', body: JSON.stringify(payload) })
export const upsertTag = (payload: TagConfigInput) => request<TagConfig>(`/tags${payload.id ? `/${payload.id}` : ''}`.replace(/\/$/, ''), { method: payload.id ? 'PUT' : 'POST', body: JSON.stringify(payload) })

export async function importFlutterDatabase(file: File, replaceExisting = true): Promise<FlutterImportSummary> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('replace_existing', String(replaceExisting))
  return request<FlutterImportSummary>('/import/flutter-db', { method: 'POST', body: formData })
}