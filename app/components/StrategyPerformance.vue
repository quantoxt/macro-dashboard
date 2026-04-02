<script setup lang="ts">
import { useStrategyPerformance } from '@/composables/useStrategyPerformance'

const { performance, pending, error } = useStrategyPerformance()

const trendIcon: Record<string, string> = {
  rising: '&#9650;',
  stable: '&#9654;',
  declining: '&#9660;',
}

const trendColor: Record<string, string> = {
  rising: 'text-[var(--bullish)]',
  stable: 'text-[var(--accent-warm)]',
  declining: 'text-[var(--bearish)]',
}
</script>

<template>
  <section>
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Strategy Performance
    </h2>

    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[rgba(239,68,68,0.15)]">
      Failed to load performance data.
    </div>

    <div v-else-if="pending" class="space-y-2">
      <div v-for="i in 3" :key="i" class="h-20 rounded-xl shimmer border border-[rgba(255,255,255,0.04)]" />
    </div>

    <div v-else class="space-y-2">
      <!-- Key Metrics -->
      <div class="border border-[rgba(255,255,255,0.07)] rounded-xl bg-[rgba(7,7,13,0.5)] px-5 py-4 transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]">
        <div class="grid grid-cols-2 gap-3">
          <!-- Win Rate -->
          <div>
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Win Rate</div>
            <div class="flex items-end gap-1.5">
              <span class="text-xl font-bold tabular-nums" :class="performance.winRate >= 60 ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'">
                {{ performance.winRate }}%
              </span>
              <span
                class="text-[10px] mb-0.5"
                :class="trendColor[performance.confidenceTrend]"
                v-html="trendIcon[performance.confidenceTrend]"
              />
            </div>
          </div>

          <!-- Profit Factor -->
          <div>
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Profit Factor</div>
            <div class="text-xl font-bold tabular-nums" :class="performance.profitFactor >= 1.5 ? 'text-[var(--bullish)]' : 'text-[var(--accent-warm)]'">
              {{ performance.profitFactor.toFixed(2) }}
            </div>
          </div>

          <!-- Avg Pips -->
          <div>
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Avg Pips</div>
            <div class="text-sm font-semibold tabular-nums">
              +{{ performance.avgPips.toFixed(1) }}
            </div>
          </div>

          <!-- Weekly PnL -->
          <div>
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Weekly P&L</div>
            <div class="text-sm font-semibold tabular-nums text-[var(--bullish)]">
              +{{ performance.weeklyPnl }}
            </div>
          </div>
        </div>
      </div>

      <!-- Streak + Recent Results -->
      <div class="border border-[rgba(255,255,255,0.07)] rounded-xl bg-[rgba(7,7,13,0.5)] px-5 py-3.5 flex items-center justify-between transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Streak</div>
          <span
            class="text-sm font-bold tabular-nums"
            :class="performance.streakType === 'wins' ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'"
          >
            {{ performance.streak }}{{ performance.streakType === 'wins' ? 'W' : 'L' }}
          </span>
        </div>

        <div class="flex items-center gap-1.5">
          <div
            v-for="(result, i) in performance.recentResults"
            :key="i"
            class="w-5 h-5 rounded-md flex items-center justify-center text-[9px] font-bold"
            :class="result === 'W'
              ? 'bg-[rgba(16,185,129,0.12)] text-[var(--bullish)]'
              : 'bg-[rgba(239,68,68,0.12)] text-[var(--bearish)]'"
          >
            {{ result }}
          </div>
        </div>
      </div>

      <!-- Total Trades + Drawdown -->
      <div class="border border-[rgba(255,255,255,0.07)] rounded-xl bg-[rgba(7,7,13,0.5)] px-5 py-3 flex items-center justify-between transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Total Trades</div>
          <div class="text-sm font-semibold tabular-nums">{{ performance.totalTrades }}</div>
        </div>
        <div class="text-right">
          <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Max DD</div>
          <div class="text-sm font-semibold tabular-nums text-[var(--bearish)]">
            {{ performance.maxDrawdown }}%
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
