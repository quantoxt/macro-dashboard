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
  <div class="min-h-screen bg-(--background) text-(--foreground)">
    <header class="anim-in border-b border-(--border) px-4 py-3 md:px-6">
      <div class="max-w-[1800px] mx-auto flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span class="w-1 h-4 rounded-full bg-(--accent-warm)" />
          <h1 class="text-sm font-semibold tracking-wide">Macro Dashboard</h1>
        </div>
        <div class="flex items-center gap-3 md:gap-4 text-xs text-(--muted-foreground)">
          <span class="inline-flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-(--bullish)" />
            Live
          </span>
          <span v-if="pending" class="tabular-nums">Loading...</span>
          <span v-else-if="formatted" class="tabular-nums">Updated {{ formatted }}</span>
        </div>
      </div>
    </header>
    <main class="max-w-[1800px] mx-auto px-4 py-4 md:px-6 md:py-6">
      <slot />
    </main>
    <footer class="border-t border-(--border) px-4 py-3 md:px-6">
      <div class="max-w-[1800px] mx-auto text-center text-xs text-(--muted-foreground)">
        © 2026 — Product of <a href="https://x.com/quantoxtinc" target="_blank" rel="noopener" class="font-semibold text-(--foreground) hover:underline">Quantoxt Inc</a>
      </div>
    </footer>
  </div>
</template>
