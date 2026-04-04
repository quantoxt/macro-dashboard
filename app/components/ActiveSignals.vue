<script setup lang="ts">
import { useActiveSignals } from '~/composables/useActiveSignals'
import type { ActiveSignal } from '~/composables/useActiveSignals'

const { signals, pending, error } = useActiveSignals()

function fmtPrice(pair: string, price: number): string {
  if (pair.includes('BTC')) return price.toFixed(0)
  if (pair.includes('JPY')) return price.toFixed(2)
  if (pair.includes('XA')) return price.toFixed(2)
  return price.toFixed(4)
}

const strategyLabel: Record<string, string> = {
  confluence_breakout: 'Confluence',
  mean_reversion: 'Mean Reversion',
  momentum_shift: 'Momentum',
}

const expanded = ref<Set<string>>(new Set())

function toggle(key: string) {
  if (expanded.value.has(key))
    expanded.value.delete(key)
  else
    expanded.value.add(key)
}

function relativeTime(iso: string): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m`
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}

function getExpiryPercent(signal: ActiveSignal): number {
  if (!signal.generatedAt || !signal.timeframe) return 0
  const limits: Record<string, number> = { H1: 8, H4: 24, D1: 48 }
  const limit = limits[signal.timeframe] || 48
  const elapsed = (Date.now() - new Date(signal.generatedAt).getTime()) / 3600000
  return Math.min(100, (elapsed / limit) * 100)
}
</script>

<template>
  <section>
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Active Signals
    </h2>

    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[var(--border-sell)]">
      {{ error }}
    </div>

    <div v-else class="space-y-2">
      <!-- Skeleton -->
      <template v-if="pending">
        <div v-for="i in 3" :key="i" class="h-[104px] rounded-xl shimmer border border-[var(--surface-skeleton)]" />
      </template>

      <!-- Empty state -->
      <template v-else-if="!signals?.length">
        <div class="text-[var(--muted-foreground)] text-xs p-6 rounded-xl border border-[var(--surface-border)] text-center">
          <p class="mb-1">No active signals</p>
          <p class="text-[10px] opacity-60">Signals appear when multiple indicators align. Refreshes every 5 min.</p>
        </div>
      </template>

      <!-- Signal cards -->
      <template v-else>
        <div
          v-for="signal in signals"
          :key="signal.pair + signal.strategy"
          class="border rounded-xl bg-[var(--surface)] overflow-hidden transition-colors duration-200 hover:border-[var(--surface-border-hover)]"
          :class="signal.direction === 'buy'
            ? 'border-[var(--border-buy)]'
            : 'border-[var(--border-sell)]'"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--separator)]">
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center justify-center w-5 h-5 rounded text-[9px] font-bold uppercase"
                :class="signal.direction === 'buy'
                  ? 'bg-[var(--badge-buy)] text-[var(--bullish)]'
                  : 'bg-[var(--badge-sell)] text-[var(--bearish)]'"
              >
                {{ signal.direction === 'buy' ? 'B' : 'S' }}
              </span>
              <span class="text-sm font-semibold">{{ signal.pair }}</span>
              <!-- Strategy badge -->
              <span class="text-[9px] px-1.5 py-0.5 rounded bg-[var(--accent-warm-muted)] text-[var(--accent-warm)]">
                {{ strategyLabel[signal.strategy] || signal.strategy }}
              </span>
              <span class="text-[10px] text-[var(--muted-foreground)]">{{ signal.timeframe }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-[var(--muted-foreground)] tabular-nums">
                R:R {{ signal.riskReward }}:1
              </span>
              <span
                class="text-sm font-bold tabular-nums"
                :class="signal.confidence >= 80 ? 'text-[var(--bullish)]' : signal.confidence >= 60 ? 'text-[var(--accent-warm)]' : 'text-[var(--muted-foreground)]'"
              >
                {{ signal.confidence }}%
              </span>
              <span class="text-[9px] text-[var(--muted-foreground)]">
                {{ relativeTime(signal.generatedAt) }}
              </span>
              <span
                v-if="signal.generatedAt && getExpiryPercent(signal) > 70"
                class="text-[8px] px-1 py-0.5 rounded bg-[var(--accent-warm-muted)] text-[var(--accent-warm)]"
              >
                expiring
              </span>
            </div>
          </div>

          <!-- Body -->
          <div class="flex flex-col md:flex-row">
            <!-- Price levels -->
            <div class="px-4 py-3 md:flex-1 md:py-2.5 flex flex-col justify-center gap-2 md:gap-1.5">
              <div class="flex items-center justify-between text-xs">
                <span class="text-[var(--muted-foreground)]">Entry</span>
                <span class="tabular-nums font-medium">{{ fmtPrice(signal.pair, signal.entry) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-[var(--muted-foreground)]">TP</span>
                <span class="tabular-nums font-medium text-[var(--bullish)]">{{ fmtPrice(signal.pair, signal.tp) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-[var(--muted-foreground)]">SL</span>
                <span class="tabular-nums font-medium text-[var(--bearish)]">{{ fmtPrice(signal.pair, signal.sl) }}</span>
              </div>
            </div>

            <!-- Separator -->
            <div class="h-px md:h-auto md:w-px mx-4 md:mx-0 md:my-3 bg-[var(--separator)]" />

            <!-- Reason -->
            <div class="flex-1 px-4 pb-3 pt-1 md:py-2.5 flex items-center gap-3">
              <!-- Vertical progress bar — desktop only -->
              <div class="hidden md:block relative w-1.5 self-stretch rounded-full bg-[var(--progress-track)] flex-shrink-0">
                <div
                  class="absolute bottom-0 w-full rounded-full transition-all duration-700"
                  :class="signal.direction === 'buy'
                    ? 'bg-gradient-to-t from-[rgba(16,185,129,0.3)] to-[var(--bullish)]'
                    : 'bg-gradient-to-t from-[rgba(239,68,68,0.3)] to-[var(--bearish)]'"
                  :style="{ height: signal.confidence + '%' }"
                />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-[10px] text-[var(--muted-foreground)] leading-relaxed line-clamp-2">
                  {{ signal.reason }}
                </p>
                <!-- Expandable reasons -->
                <button
                  v-if="(signal.reasons?.length ?? 0) > 1"
                  class="text-[9px] text-[var(--accent-warm)] mt-1 hover:underline"
                  @click="toggle(signal.pair + signal.strategy)"
                >
                  {{ expanded.has(signal.pair + signal.strategy) ? 'Show less' : `${signal.reasons.length} reasons` }}
                </button>
                <ul
                  v-if="expanded.has(signal.pair + signal.strategy) && signal.reasons?.length"
                  class="mt-1.5 space-y-0.5"
                >
                  <li
                    v-for="(r, i) in signal.reasons"
                    :key="i"
                    class="text-[9px] text-[var(--muted-foreground)] pl-2 border-l border-[var(--separator)]"
                  >
                    {{ r }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>
