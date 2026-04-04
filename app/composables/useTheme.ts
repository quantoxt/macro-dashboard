export type Theme = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'macro-dashboard-theme'

const state = ref<{
  theme: Theme
  resolved: 'light' | 'dark'
}>({
  theme: 'system',
  resolved: 'dark',
})

let listenerAttached = false

function getSystemPreference(): 'light' | 'dark' {
  if (import.meta.server) return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(r: 'light' | 'dark') {
  if (!import.meta.client) return
  const el = document.documentElement
  el.classList.remove('light', 'dark')
  el.classList.add(r)
  el.setAttribute('data-theme', r)
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', r === 'dark' ? '#07070d' : '#f8f9fb')
}

function setTheme(t: Theme) {
  state.value.theme = t
  if (import.meta.client) {
    localStorage.setItem(STORAGE_KEY, t)
  }
  const r = t === 'system' ? getSystemPreference() : t
  state.value.resolved = r
  applyTheme(r)
}

function attachSystemListener() {
  if (listenerAttached || import.meta.server) return
  listenerAttached = true
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  mq.addEventListener('change', () => {
    if (state.value.theme === 'system') {
      const r = mq.matches ? 'dark' : 'light'
      state.value.resolved = r
      applyTheme(r)
    }
  })
}

export function useTheme() {
  // Initialize eagerly on client — runs during setup(), not in onMounted
  if (import.meta.client && !listenerAttached) {
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null
    if (stored && ['light', 'dark', 'system'].includes(stored)) {
      state.value.theme = stored
    }
    const r = state.value.theme === 'system' ? getSystemPreference() : state.value.theme
    state.value.resolved = r
    state.value // touch reactivity
    applyTheme(r)
    attachSystemListener()
  }

  return {
    theme: computed(() => state.value.theme),
    resolved: computed(() => state.value.resolved),
    setTheme,
  }
}
