<script setup lang="ts">
import { Sun, Moon, Monitor, FlaskConical, Settings, History, Send } from 'lucide-vue-next'
import type { Theme } from '@/composables/useTheme'

const { formatted, pending } = useLastUpdated()
const { theme, setTheme } = useTheme()

const route = useRoute()

const themes: { value: Theme; icon: any; label: string }[] = [
  { value: 'light', icon: Sun, label: 'Light' },
  { value: 'dark', icon: Moon, label: 'Dark' },
  { value: 'system', icon: Monitor, label: 'System' },
]

useHead({
  link: [
    { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
    { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap',
    },
  ],
})
</script>

<template>
  <div class="min-h-screen flex flex-col text-[var(--foreground)] relative overflow-x-hidden">
    <!-- Atmospheric gradient background -->
    <div class="fixed inset-0 -z-10" :style="{ background: 'var(--page-bg)' }" />
    <div class="fixed inset-0 -z-10" :style="{ background: 'var(--page-gradient)' }" />

    <!-- Header -->
    <header class="glass-header sticky top-0 z-50 border-b border-[var(--header-border)] px-4 py-3 md:px-6">
      <div class="max-w-[1800px] mx-auto flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <NuxtLink to="/" class="flex items-center gap-2.5">
            <span class="w-1 h-4 rounded-full bg-[var(--accent-warm)]" />
            <h1 class="text-sm font-semibold tracking-wide text-gradient-heading">Macro Dashboard</h1>
          </NuxtLink>

          <!-- Nav links -->
          <div class="hidden md:flex items-center gap-1 ml-4">
            <NuxtLink
              to="/signals"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all duration-200"
              :class="route.path === '/signals'
                ? 'bg-[var(--surface)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
            >
              <History class="w-3 h-3" />
              Signals
            </NuxtLink>
            <NuxtLink
              to="/backtest"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all duration-200"
              :class="route.path === '/backtest'
                ? 'bg-[var(--surface)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
            >
              <FlaskConical class="w-3 h-3" />
              Backtest
            </NuxtLink>
            <NuxtLink
              to="/telegram"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all duration-200"
              :class="route.path === '/telegram'
                ? 'bg-[var(--surface)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
            >
              <Send class="w-3 h-3" />
              Telegram
            </NuxtLink>
            <NuxtLink
              to="/settings"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all duration-200"
              :class="route.path === '/settings'
                ? 'bg-[var(--surface)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
            >
              <Settings class="w-3 h-3" />
              Settings
            </NuxtLink>
          </div>
        </div>

        <div class="flex items-center gap-3 md:gap-4 text-xs text-[var(--muted-foreground)]">
          <!-- Mobile nav -->
          <div class="flex md:hidden items-center gap-1">
            <NuxtLink
              to="/signals"
              class="p-1.5 rounded-md transition-all duration-200"
              :class="route.path === '/signals' ? 'text-[var(--foreground)]' : 'text-[var(--muted-foreground)]'"
              aria-label="Signals"
            >
              <History class="w-3.5 h-3.5" />
            </NuxtLink>
            <NuxtLink
              to="/backtest"
              class="p-1.5 rounded-md transition-all duration-200"
              :class="route.path === '/backtest' ? 'text-[var(--foreground)]' : 'text-[var(--muted-foreground)]'"
              aria-label="Backtest"
            >
              <FlaskConical class="w-3.5 h-3.5" />
            </NuxtLink>
            <NuxtLink
              to="/telegram"
              class="p-1.5 rounded-md transition-all duration-200"
              :class="route.path === '/telegram' ? 'text-[var(--foreground)]' : 'text-[var(--muted-foreground)]'"
              aria-label="Telegram"
            >
              <Send class="w-3.5 h-3.5" />
            </NuxtLink>
            <NuxtLink
              to="/settings"
              class="p-1.5 rounded-md transition-all duration-200"
              :class="route.path === '/settings' ? 'text-[var(--foreground)]' : 'text-[var(--muted-foreground)]'"
              aria-label="Settings"
            >
              <Settings class="w-3.5 h-3.5" />
            </NuxtLink>
          </div>

          <!-- Theme toggle -->
          <div class="flex items-center gap-0.5 bg-[var(--surface-skeleton)] rounded-lg p-0.5">
            <button
              v-for="t in themes"
              :key="t.value"
              @click="setTheme(t.value)"
              class="p-1.5 rounded-md transition-all duration-200"
              :class="theme === t.value
                ? 'bg-[var(--surface)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
              :title="t.label"
              :aria-label="`Switch to ${t.label} theme`"
            >
              <component :is="t.icon" class="w-3.5 h-3.5" />
            </button>
          </div>

          <span class="hidden sm:inline-flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-[var(--bullish)] live-pulse" />
            Live
          </span>
          <span v-if="pending" class="tabular-nums hidden sm:inline">Loading...</span>
          <span v-else-if="formatted" class="tabular-nums hidden sm:inline">Updated {{ formatted }}</span>
        </div>
      </div>
    </header>

    <main class="flex-1 max-w-[1800px] mx-auto w-full px-4 py-5 md:px-6 md:py-6">
      <slot />
    </main>

    <footer class="border-t border-[var(--footer-border)] px-4 py-4 md:px-6">
      <div class="max-w-[1800px] mx-auto text-center text-[10px] text-[var(--muted-foreground)]">
        &copy; 2026 &mdash; Product of <a href="https://x.com/quantoxtinc" target="_blank" rel="noopener" class="font-semibold text-[var(--foreground)] hover:text-[var(--accent-warm)] transition-colors">Quantoxt Inc</a>
      </div>
    </footer>
  </div>
</template>
