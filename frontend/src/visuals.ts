export const colorTokens = ['petrol', 'emerald', 'gold', 'terracotta', 'sky', 'plum', 'amber', 'coral', 'sage'] as const
export const iconTokens = ['home', 'bolt', 'water', 'tv', 'school', 'restaurant', 'commute', 'group', 'favorite', 'savings', 'trending', 'receipt', 'work', 'briefcase', 'redeem', 'account_balance', 'paid', 'apartment'] as const

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
}

export function iconGlyph(token: string): string {
  return iconGlyphMap[token] ?? '◼'
}

export function tokenColor(token: string): string {
  return `var(--${token})`
}

export function slugify(input: string): string {
  const normalized = input.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')
  const compact = normalized.replace(/-{2,}/g, '-').replace(/^-|-$/g, '')
  return compact || String(Date.now())
}