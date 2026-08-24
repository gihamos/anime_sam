import { create } from 'zustand'

type Theme = 'dark' | 'light'

const STORAGE_KEY = 'anime_sama_admin_theme'

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

const initial: Theme = (localStorage.getItem(STORAGE_KEY) as Theme | null) ?? 'dark'
applyTheme(initial)

interface ThemeState {
  theme: Theme
  toggle: () => void
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initial,
  toggle: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark'
    localStorage.setItem(STORAGE_KEY, next)
    applyTheme(next)
    set({ theme: next })
  },
}))
