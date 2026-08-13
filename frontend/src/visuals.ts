export const colorTokens = ['petrol', 'emerald', 'gold', 'terracotta', 'sky', 'plum', 'amber', 'coral', 'sage'] as const
export const iconTokens = ['home', 'bolt', 'water', 'tv', 'school', 'restaurant', 'commute', 'group', 'favorite', 'savings', 'trending', 'receipt', 'work', 'briefcase', 'redeem', 'account_balance', 'paid', 'apartment', 'credit_card', 'movie', 'health'] as const

const iconGlyphMap: Record<string, string> = {
  home: '🏠',
  bolt: '⚡',
  water: '💧',
  tv: '📺',
  school: '🎓',
  restaurant: '🍽️',
  commute: '🚌',
  group: '👥',
  favorite: '❤️',
  savings: '💰',
  trending: '📈',
  receipt: '🧾',
  work: '🛠️',
  briefcase: '💼',
  redeem: '🎁',
  account_balance: '🏦',
  paid: '💵',
  apartment: '🏢',
  credit_card: '💳',
  movie: '🎬',
  health: '🩺',
}

const iconLabelMap: Record<string, string> = {
  home: 'Casa',
  bolt: 'Luz',
  water: 'Agua',
  tv: 'TV',
  school: 'Colegio',
  restaurant: 'Comida',
  commute: 'Transporte',
  group: 'Grupo',
  favorite: 'Favorito',
  savings: 'Ahorro',
  trending: 'Inversion',
  receipt: 'Recibo',
  work: 'Trabajo',
  briefcase: 'Oficina',
  redeem: 'Regalo',
  account_balance: 'Banco',
  paid: 'Pago',
  apartment: 'Renta',
  credit_card: 'Tarj. cred.',
  movie: 'Entreten.',
  health: 'Salud',
}

export function iconGlyph(token: string): string {
  return iconGlyphMap[token] ?? '◼'
}

export function iconLabel(token: string): string {
  return iconLabelMap[token] ?? token
}

export function tokenColor(token: string): string {
  return `var(--${token})`
}

export function slugify(input: string): string {
  const normalized = input.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')
  const compact = normalized.replace(/-{2,}/g, '-').replace(/^-|-$/g, '')
  return compact || String(Date.now())
}