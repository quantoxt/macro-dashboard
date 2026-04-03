<script setup lang="ts">
import { useMarketPulse } from '@/composables/useMarketPulse'

const { pulse, pending, error } = useMarketPulse()

const regimeColors: Record<string, string> = {
  'risk-on': 'text-[var(--bullish)] bg-[var(--badge-buy)]',
  'risk-off': 'text-[var(--bearish)] bg-[var(--badge-sell)]',
  'neutral': 'text-[var(--accent-warm)] bg-[var(--badge-warn)]',
}

const volatilityColors: Record<string, string> = {
  'Low': 'text-[var(--bullish)]',
  'Moderate': 'text-[var(--accent-warm)]',
  'High': 'text-[var(--bearish)]',
}
</script>

<template>
  <section>
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Market Pulse
    </h2>

    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[var(--border-sell)]">
      Failed to load market data.
    </div>

    <div v-else-if="pending" class="rounded-xl shimmer border border-[var(--surface-skeleton)] h-[280px]" />

    <div
      v-else
      class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-5 py-5 space-y-4 transition-colors duration-200 hover:border-[var(--surface-border-hover)]"
    >
      <!-- Session -->
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Session</span>
        <div class="text-right">
          <div class="text-sm font-semibold">{{ pulse.session }}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">{{ pulse.sessionTime }}</div>
        </div>
      </div>

      <div class="h-px bg-[var(--separator-subtle)]" />

      <!-- Regime -->
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Regime</span>
        <div class="flex items-center gap-2">
          <span
            class="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold"
            :class="regimeColors[pulse.regime]"
          >
            {{ pulse.regime }}
          </span>
          <span class="text-[10px] text-[var(--muted-foreground)] tabular-nums">{{ pulse.regimeConfidence }}%</span>
        </div>
      </div>

      <div class="h-px bg-[var(--separator-subtle)]" />

      <!-- Volatility -->
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Volatility</span>
        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold tabular-nums">{{ pulse.volatilityIndex }}</span>
          <span class="text-[10px] font-medium" :class="volatilityColors[pulse.volatilityLabel]">
            {{ pulse.volatilityLabel }}
          </span>
        </div>
      </div>

      <div class="h-px bg-[var(--separator-subtle)]" />

      <!-- News + Consolidation -->
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Alerts</span>
        <div class="flex items-center gap-2">
          <span
            v-if="pulse.newsWarnings > 0"
            class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-[var(--badge-warn)] text-[var(--accent-warm)]"
          >
            {{ pulse.newsWarnings }} news
          </span>
          <span class="text-[10px] text-[var(--muted-foreground)]">
            {{ pulse.consolidationPairs.length }} ranging
          </span>
        </div>
      </div>

      <div class="h-px bg-[var(--separator-subtle)]" />

      <!-- Next Event -->
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Next Event</span>
        <div class="text-right">
          <div class="text-xs font-medium">{{ pulse.nextEvent }}</div>
          <div class="text-[10px] text-[var(--accent-warm)]">{{ pulse.nextEventTime }}</div>
        </div>
      </div>
    </div>
  </section>
</template>
