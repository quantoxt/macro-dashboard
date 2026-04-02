<script setup lang="ts">
const { formatted, pending } = useLastUpdated()

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
  <div class="min-h-screen text-[var(--foreground)] relative overflow-x-hidden">
    <!-- Atmospheric gradient background -->
    <div class="fixed inset-0 -z-10" style="background: #07070d;" />
    <div class="fixed inset-0 -z-10" style="background: radial-gradient(ellipse 80% 60% at 10% 20%, rgba(30, 30, 80, 0.15), transparent), radial-gradient(ellipse 60% 50% at 85% 70%, rgba(60, 20, 70, 0.08), transparent), radial-gradient(ellipse 70% 40% at 50% 100%, rgba(20, 25, 50, 0.12), transparent);" />

    <!-- Header -->
    <header class="glass-header sticky top-0 z-50 border-b border-[rgba(255,255,255,0.06)] px-4 py-3 md:px-6">
      <div class="max-w-[1800px] mx-auto flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span class="w-1 h-4 rounded-full bg-[var(--accent-warm)]" />
          <h1 class="text-sm font-semibold tracking-wide text-gradient-heading">Macro Dashboard</h1>
        </div>
        <div class="flex items-center gap-3 md:gap-4 text-xs text-[var(--muted-foreground)]">
          <span class="inline-flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-[var(--bullish)] live-pulse" />
            Live
          </span>
          <span v-if="pending" class="tabular-nums">Loading...</span>
          <span v-else-if="formatted" class="tabular-nums">Updated {{ formatted }}</span>
        </div>
      </div>
    </header>

    <main class="max-w-[1800px] mx-auto px-4 py-5 md:px-6 md:py-6">
      <slot />
    </main>

    <footer class="border-t border-[rgba(255,255,255,0.04)] px-4 py-4 md:px-6">
      <div class="max-w-[1800px] mx-auto text-center text-[10px] text-[var(--muted-foreground)]">
        &copy; 2026 &mdash; Product of <a href="https://x.com/quantoxtinc" target="_blank" rel="noopener" class="font-semibold text-[var(--foreground)] hover:text-[var(--accent-warm)] transition-colors">Quantoxt Inc</a>
      </div>
    </footer>
  </div>
</template>
