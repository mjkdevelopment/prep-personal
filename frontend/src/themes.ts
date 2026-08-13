export interface ThemePalette {
  id: string
  name: string
  description: string
  fontDisplay: string
  fontBody: string
  ivory: string
  paper: string
  sand: string
  petrol: string
  emerald: string
  gold: string
  terracotta: string
  sky: string
  plum: string
  amber: string
  coral: string
  sage: string
  slate: string
  ink: string
  panelBg: string
  cardShadow: string
  heroGradient: string
  activeGradient: string
  inputBg: string
  pageGradient: string
  radius: string
}

export const themeStorageKey = 'gride-ledger-theme'

export const palettes: ThemePalette[] = [
  {
    id: 'emerald_editorial',
    name: 'Emerald Editorial',
    description: 'Sobria, premium y con aire de revista financiera.',
    fontDisplay: "Georgia, 'Times New Roman', serif",
    fontBody: "'Trebuchet MS', 'Segoe UI', sans-serif",
    ivory: '#F8F4EC',
    paper: '#FFFCF7',
    sand: '#E9E1D4',
    petrol: '#1D3C3C',
    emerald: '#335F52',
    gold: '#C29A4B',
    terracotta: '#B26B52',
    sky: '#7FA8B2',
    plum: '#8576A8',
    amber: '#D0A55E',
    coral: '#D78363',
    sage: '#8BA37B',
    slate: '#57615D',
    ink: '#1A1E1C',
    panelBg: 'linear-gradient(180deg, rgba(255,255,255,0.9), rgba(248,244,236,0.94))',
    cardShadow: '0 18px 40px rgba(29, 60, 60, 0.08)',
    heroGradient: 'radial-gradient(circle at top left, rgba(194,154,75,0.34), transparent 36%), linear-gradient(135deg, #173939, #274b46 58%, #8c6a2f)',
    activeGradient: 'linear-gradient(135deg, #335F52, #C29A4B)',
    inputBg: 'rgba(255,255,255,0.92)',
    pageGradient: 'radial-gradient(circle at top left, rgba(194,154,75,0.33), transparent 30%), radial-gradient(circle at top right, rgba(127,168,178,0.22), transparent 22%), linear-gradient(180deg, #f7f1e7 0%, #fdfbf7 42%, #e9e1d4 100%)',
    radius: '28px',
  },
  {
    id: 'ocean_ledger',
    name: 'Ocean Ledger',
    description: 'Mas corporativa y tecnica, con un tono de cabina de mando.',
    fontDisplay: "'Gill Sans', 'Segoe UI', sans-serif",
    fontBody: "Verdana, 'Segoe UI', sans-serif",
    ivory: '#EAF7FF',
    paper: '#F7FCFF',
    sand: '#CCE7F4',
    petrol: '#08273B',
    emerald: '#1B7FA9',
    gold: '#5ED0FF',
    terracotta: '#FF8B6A',
    sky: '#49B8E8',
    plum: '#4B73A6',
    amber: '#9CE9FF',
    coral: '#FF7E6A',
    sage: '#5FB3B8',
    slate: '#4E6E84',
    ink: '#081C28',
    panelBg: 'linear-gradient(180deg, rgba(255,255,255,0.78), rgba(221,244,255,0.9))',
    cardShadow: '0 22px 54px rgba(8, 39, 59, 0.22)',
    heroGradient: 'radial-gradient(circle at top right, rgba(94,208,255,0.48), transparent 34%), linear-gradient(135deg, #061C2D, #0A4E73 52%, #10A9D9)',
    activeGradient: 'linear-gradient(135deg, #0B5D84, #5ED0FF)',
    inputBg: 'rgba(242,251,255,0.92)',
    pageGradient: 'radial-gradient(circle at 10% 10%, rgba(94,208,255,0.26), transparent 24%), radial-gradient(circle at 100% 0%, rgba(9,89,132,0.36), transparent 28%), linear-gradient(180deg, #d8f2ff 0%, #f4fbff 38%, #bcdced 100%)',
    radius: '18px',
  },
  {
    id: 'terracotta_luxe',
    name: 'Terracotta Luxe',
    description: 'Mas calida y boutique, con contraste cobrizo marcado.',
    fontDisplay: "'Palatino Linotype', Georgia, serif",
    fontBody: "'Lucida Sans Unicode', 'Segoe UI', sans-serif",
    ivory: '#FFF2EA',
    paper: '#FFF9F4',
    sand: '#F3D7C8',
    petrol: '#6B2F21',
    emerald: '#7D4F2A',
    gold: '#E5A64D',
    terracotta: '#C55A39',
    sky: '#D9A88F',
    plum: '#8E5B64',
    amber: '#FFBF66',
    coral: '#E77952',
    sage: '#A0886C',
    slate: '#7C5A4C',
    ink: '#2B140E',
    panelBg: 'linear-gradient(180deg, rgba(255,249,244,0.9), rgba(248,224,210,0.96))',
    cardShadow: '0 24px 52px rgba(107, 47, 33, 0.16)',
    heroGradient: 'radial-gradient(circle at top left, rgba(255,191,102,0.34), transparent 32%), linear-gradient(135deg, #5B2417, #A9482B 58%, #F0A24F)',
    activeGradient: 'linear-gradient(135deg, #A9482B, #F0A24F)',
    inputBg: 'rgba(255,246,239,0.94)',
    pageGradient: 'radial-gradient(circle at top left, rgba(255,191,102,0.24), transparent 28%), radial-gradient(circle at top right, rgba(197,90,57,0.18), transparent 24%), linear-gradient(180deg, #fff1e7 0%, #fff8f2 40%, #edcdbd 100%)',
    radius: '32px',
  },
  {
    id: 'sage_sun',
    name: 'Sage & Sun',
    description: 'Mas organica y luminosa, casi como una libreta domestica premium.',
    fontDisplay: "Candara, 'Trebuchet MS', sans-serif",
    fontBody: "'Segoe UI', Tahoma, sans-serif",
    ivory: '#F5F8E4',
    paper: '#FFFFFA',
    sand: '#DFE9BB',
    petrol: '#496146',
    emerald: '#8DA45E',
    gold: '#F1C94C',
    terracotta: '#F08A46',
    sky: '#94C8BC',
    plum: '#7E8D62',
    amber: '#FFD970',
    coral: '#F59D67',
    sage: '#A4BE65',
    slate: '#697756',
    ink: '#232A1C',
    panelBg: 'linear-gradient(180deg, rgba(255,255,250,0.94), rgba(235,242,206,0.95))',
    cardShadow: '0 18px 42px rgba(73, 97, 70, 0.14)',
    heroGradient: 'radial-gradient(circle at top center, rgba(255,217,112,0.38), transparent 30%), linear-gradient(135deg, #506C43, #84A056 58%, #E5A646)',
    activeGradient: 'linear-gradient(135deg, #7E9A4E, #F1C94C)',
    inputBg: 'rgba(255,255,248,0.96)',
    pageGradient: 'radial-gradient(circle at top left, rgba(255,217,112,0.26), transparent 26%), radial-gradient(circle at bottom right, rgba(141,164,94,0.18), transparent 28%), linear-gradient(180deg, #f3f8dc 0%, #fffef7 46%, #d9e4af 100%)',
    radius: '24px',
  },
  {
    id: 'plum_finance',
    name: 'Plum Finance',
    description: 'Mas audaz y nocturna, con presencia de producto digital.',
    fontDisplay: "Garamond, Georgia, serif",
    fontBody: "Arial, 'Segoe UI', sans-serif",
    ivory: '#F5EFF9',
    paper: '#FFFCFF',
    sand: '#E4D7EE',
    petrol: '#311B45',
    emerald: '#6A3FA0',
    gold: '#D168A2',
    terracotta: '#39A4A1',
    sky: '#8CA6E8',
    plum: '#8A58C3',
    amber: '#E68BB8',
    coral: '#58C5BE',
    sage: '#7E8BC0',
    slate: '#6A5F83',
    ink: '#1F1428',
    panelBg: 'linear-gradient(180deg, rgba(255,252,255,0.82), rgba(236,224,246,0.92))',
    cardShadow: '0 24px 58px rgba(49, 27, 69, 0.2)',
    heroGradient: 'radial-gradient(circle at top right, rgba(209,104,162,0.42), transparent 34%), linear-gradient(135deg, #241333, #5B2F82 54%, #39A4A1)',
    activeGradient: 'linear-gradient(135deg, #6A3FA0, #D168A2)',
    inputBg: 'rgba(253,248,255,0.94)',
    pageGradient: 'radial-gradient(circle at top left, rgba(209,104,162,0.24), transparent 26%), radial-gradient(circle at top right, rgba(57,164,161,0.18), transparent 28%), linear-gradient(180deg, #f3ebf9 0%, #fffaff 42%, #dbc8ec 100%)',
    radius: '20px',
  },
]

export function getStoredTheme(): string {
  if (typeof window === 'undefined') {
    return palettes[0].id
  }
  return window.localStorage.getItem(themeStorageKey) ?? palettes[0].id
}

export function applyTheme(themeId: string): void {
  const palette = palettes.find((item) => item.id === themeId) ?? palettes[0]
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(themeStorageKey, palette.id)
  }
  const root = document.documentElement
  root.dataset.theme = palette.id
  root.style.setProperty('--ivory', palette.ivory)
  root.style.setProperty('--paper', palette.paper)
  root.style.setProperty('--sand', palette.sand)
  root.style.setProperty('--petrol', palette.petrol)
  root.style.setProperty('--emerald', palette.emerald)
  root.style.setProperty('--gold', palette.gold)
  root.style.setProperty('--terracotta', palette.terracotta)
  root.style.setProperty('--sky', palette.sky)
  root.style.setProperty('--plum', palette.plum)
  root.style.setProperty('--amber', palette.amber)
  root.style.setProperty('--coral', palette.coral)
  root.style.setProperty('--sage', palette.sage)
  root.style.setProperty('--slate', palette.slate)
  root.style.setProperty('--ink', palette.ink)
  root.style.setProperty('--font-display', palette.fontDisplay)
  root.style.setProperty('--font-body', palette.fontBody)
  root.style.setProperty('--panel-bg', palette.panelBg)
  root.style.setProperty('--card-shadow', palette.cardShadow)
  root.style.setProperty('--hero-gradient', palette.heroGradient)
  root.style.setProperty('--active-gradient', palette.activeGradient)
  root.style.setProperty('--input-bg', palette.inputBg)
  root.style.setProperty('--radius-xl', palette.radius)
  root.style.setProperty('--muted', palette.slate)
  root.style.setProperty('--muted-strong', palette.petrol)
  root.style.setProperty('--line', `${palette.petrol}22`)
  root.style.setProperty('--accent', palette.gold)
  root.style.setProperty('--accent-2', palette.emerald)
  root.style.setProperty('--page-gradient', palette.pageGradient)
}