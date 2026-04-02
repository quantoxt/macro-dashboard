<script setup lang="ts">
import { useActiveSignals } from '@/composables/useActiveSignals'

const { signals, pending, error } = useActiveSignals()

function fmtPrice(pair: string, price: number): string {
  return pair.includes('JPY') ? price.toFixed(2) : price.toFixed(4)
}
</script>

<template>
  <section>
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Active Signals
    </h2>

    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[rgba(239,68,68,0.15)]">
      Failed to load signals. Retrying...
    </div>

    <div v-else class="space-y-2">
      <!-- Skeleton -->
      <template v-if="pending">
        <div v-for="i in 5" :key="i" class="h-[104px] rounded-xl shimmer border border-[rgba(255,255,255,0.04)]" />
      </template>

      <!-- Signal cards -->
      <template v-else>
        <div
          v-for="signal in signals"
          :key="signal.pair"
          class="border rounded-xl bg-[rgba(7,7,13,0.5)] overflow-hidden transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]"
          :class="signal.direction === 'buy'
            ? 'border-[rgba(16,185,129,0.15)]'
            : 'border-[rgba(239,68,68,0.15)]'"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-4 py-2 border-b border-[rgba(255,255,255,0.06)]">
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center justify-center w-5 h-5 rounded text-[9px] font-bold uppercase"
                :class="signal.direction === 'buy'
                  ? 'bg-[rgba(16,185,129,0.12)] text-[var(--bullish)]'
                  : 'bg-[rgba(239,68,68,0.12)] text-[var(--bearish)]'"
              >
                {{ signal.direction === 'buy' ? 'B' : 'S' }}
              </span>
              <span class="text-sm font-semibold">{{ signal.pair }}</span>
              <span class="text-[10px] text-[var(--muted-foreground)]">{{ signal.timeframe }}</span>
            </div>
            <span
              class="text-sm font-bold tabular-nums"
              :class="signal.confidence >= 80 ? 'text-[var(--bullish)]' : signal.confidence >= 60 ? 'text-[var(--accent-warm)]' : 'text-[var(--muted-foreground)]'"
            >
              {{ signal.confidence }}%
            </span>
          </div>

          <!-- Body -->
          <div class="flex">
            <!-- Left: Price levels -->
            <div class="flex-1 px-4 py-2.5 flex flex-col justify-center gap-1.5">
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

            <!-- Vertical separator -->
            <div class="w-px my-3 bg-[rgba(255,255,255,0.06)]" />

            <!-- Right: Progress bar + Reason -->
            <div class="flex-1 px-4 py-2.5 flex items-center gap-3">
              <div class="relative w-1.5 self-stretch rounded-full bg-[rgba(255,255,255,0.04)] flex-shrink-0">
                <div
                  class="absolute bottom-0 w-full rounded-full transition-all duration-700"
                  :class="signal.direction === 'buy'
                    ? 'bg-gradient-to-t from-[rgba(16,185,129,0.3)] to-[var(--bullish)]'
                    : 'bg-gradient-to-t from-[rgba(239,68,68,0.3)] to-[var(--bearish)]'"
                  :style="{ height: signal.confidence + '%' }"
                />
              </div>
              <p class="text-[10px] text-[var(--muted-foreground)] leading-relaxed line-clamp-3">
                {{ signal.reason }}
              </p>
            </div>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>
