<script setup lang="ts">
import { useMarketPulse } from '@/composables/useMarketPulse'

const { pulse, pending, error } = useMarketPulse()

const regimeColors: Record<string, string> = {
  'risk-on': 'text-[var(--bullish)] bg-[rgba(16,185,129,0.1)]',
  'risk-off': 'text-[var(--bearish)] bg-[rgba(239,68,68,0.1)]',
  'neutral': 'text-[var(--accent-warm)] bg-[rgba(245,158,11,0.1)]',
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

    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[rgba(239,68,68,0.15)]">
      Failed to load market data.
    </div>

    <div v-else-if="pending" class="rounded-xl shimmer border border-[rgba(255,255,255,0.04)] h-[280px]" />

    <div
      v-else
      class="border border-[rgba(255,255,255,0.07)] rounded-xl bg-[rgba(7,7,13,0.5)] px-5 py-5 space-y-4 transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]"
    >
      <!-- Session -->
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Session</span>
        <div class="text-right">
          <div class="text-sm font-semibold">{{ pulse.session }}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">{{ pulse.sessionTime }}</div>
        </div>
      </div>

      <div class="h-px bg-[rgba(255,255,255,0.05)]" />

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

      <div class="h-px bg-[rgba(255,255,255,0.05)]" />

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

      <div class="h-px bg-[rgba(255,255,255,0.05)]" />

      <!-- News + Consolidation -->
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Alerts</span>
        <div class="flex items-center gap-2">
          <span
            v-if="pulse.newsWarnings > 0"
            class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-[rgba(245,158,11,0.1)] text-[var(--accent-warm)]"
          >
            {{ pulse.newsWarnings }} news
          </span>
          <span class="text-[10px] text-[var(--muted-foreground)]">
            {{ pulse.consolidationPairs.length }} ranging
          </span>
        </div>
      </div>

      <div class="h-px bg-[rgba(255,255,255,0.05)]" />

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
