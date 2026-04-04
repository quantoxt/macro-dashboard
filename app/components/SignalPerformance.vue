<script setup lang="ts">
import { useTracker } from '@/composables/useTracker'

const { performance, stats, pending, error } = useTracker()

const strategyLabels: Record<string, string> = {
  confluence_breakout: 'Confluence',
  mean_reversion: 'Mean Reversion',
  momentum_shift: 'Momentum',
}

function fmtPips(v: number) {
  return (v >= 0 ? '+' : '') + v.toFixed(0)
}

function fmtPct(v: number) {
  return (v * 100).toFixed(1) + '%'
}

function pnlColor(v: number): string {
  return v > 0 ? 'text-[var(--bullish)]' : v < 0 ? 'text-[var(--bearish)]' : 'text-[var(--muted-foreground)]'
}
</script>

<template>
  <section>
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Signal Performance
    </h2>

    <!-- Error state -->
    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[var(--border-sell)]">
      {{ error }}
    </div>

    <!-- Skeleton -->
    <template v-else-if="pending">
      <div class="space-y-2">
        <div class="h-14 rounded-xl shimmer border border-[var(--surface-skeleton)]" />
        <div class="h-24 rounded-xl shimmer border border-[var(--surface-skeleton)]" />
      </div>
    </template>

    <template v-else>
      <!-- Overall stats bar -->
      <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-5 py-3.5 mb-2 flex items-center justify-between transition-colors duration-200 hover:border-[var(--surface-border-hover)]">
        <div class="flex items-center gap-4 text-xs">
          <div>
            <span class="text-[var(--muted-foreground)]">Signals</span>
            <span class="ml-1.5 font-semibold tabular-nums">{{ stats.total }}</span>
          </div>
          <div>
            <span class="text-[var(--muted-foreground)]">WR</span>
            <span class="ml-1.5 font-semibold tabular-nums" :class="stats.winRate >= 0.5 ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'">{{ fmtPct(stats.winRate) }}</span>
          </div>
          <div>
            <span class="text-[var(--muted-foreground)]">PnL</span>
            <span class="ml-1.5 font-semibold tabular-nums" :class="pnlColor(stats.totalPnlPips)">{{ fmtPips(stats.totalPnlPips) }} pips</span>
          </div>
        </div>
        <div class="flex items-center gap-2 text-[10px] text-[var(--muted-foreground)]">
          <span>{{ stats.wins }}W</span>
          <span>/</span>
          <span>{{ stats.losses }}L</span>
          <span>/</span>
          <span>{{ stats.expired }}E <span class="text-[8px] opacity-60">({{ stats.expiredTime || 0 }}t/{{ stats.expiredAdverse || 0 }}a)</span></span>
          <span>/</span>
          <span>{{ stats.pending }} pending</span>
        </div>
      </div>

      <!-- Per-strategy cards -->
      <div v-if="performance" class="space-y-2">
        <div
          v-for="([sKey, perf], idx) in Object.entries(performance.strategies)"
          :key="idx"
          class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-5 py-3.5 transition-colors duration-200 hover:border-[var(--surface-border-hover)]"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold">{{ strategyLabels[sKey] || sKey }}</span>
            <span class="text-sm font-bold tabular-nums" :class="pnlColor(perf.totalPnlPips)">{{ fmtPips(perf.totalPnlPips) }} pips</span>
          </div>
          <div class="flex items-center gap-3 text-[10px] text-[var(--muted-foreground)]">
            <span>{{ perf.wins }}W / {{ perf.losses }}L / {{ perf.expired }}E <span class="text-[8px] opacity-60">({{ perf.expiredTime || 0 }}t/{{ perf.expiredAdverse || 0 }}a)</span> / {{ perf.pending }} pending</span>
            <span class="mx-auto" />
            <span class="font-semibold" :class="perf.winRate >= 0.5 ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'">{{ fmtPct(perf.winRate) }}</span>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="text-[var(--muted-foreground)] text-xs p-6 rounded-xl border border-[var(--surface-border)] text-center">
        <p>No performance data yet</p>
        <p class="text-[10px] opacity-60">Performance stats appear once signals are tracked and resolved.</p>
      </div>
    </template>
  </section>
</template>
