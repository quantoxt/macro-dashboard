<script setup lang="ts">
import { useBacktest, type BacktestParams, type BacktestTrade } from '@/composables/useBacktest'
import type { BacktestMetrics } from '@/composables/useBacktest'

const { loading, error, result, runBacktest } = useBacktest()

const INSTRUMENTS = ['XAUUSD', 'XAGUSD', 'USDJPY', 'GBPJPY', 'BTCUSD']
const STRATEGIES = ['confluence_breakout', 'mean_reversion', 'momentum_shift']
const strategyLabels: Record<string, string> = {
  confluence_breakout: 'Confluence Breakout',
  mean_reversion: 'Mean Reversion',
  momentum_shift: 'Momentum Shift',
}

const form = reactive({
  instruments: ['XAUUSD'] as string[],
  strategies: ['confluence_breakout'] as string[],
  startDate: '2025-10-01',
  endDate: '2026-03-31',
  timeframe: '1h',
})

function toggleInstrument(inst: string) {
  const idx = form.instruments.indexOf(inst)
  if (idx >= 0 && form.instruments.length > 1) form.instruments.splice(idx, 1)
  else if (idx < 0) form.instruments.push(inst)
}

function toggleStrategy(s: string) {
  const idx = form.strategies.indexOf(s)
  if (idx >= 0 && form.strategies.length > 1) form.strategies.splice(idx, 1)
  else if (idx < 0) form.strategies.push(s)
}

function handleRun() {
  runBacktest({ ...form } as BacktestParams)
}

function fmtPips(v: number) {
  return (v >= 0 ? '+' : '') + v.toFixed(1)
}

function fmtPct(v: number) {
  return (v * 100).toFixed(1) + '%'
}

function pnlClass(v: number): string {
  return v > 0 ? 'text-[var(--bullish)]' : v < 0 ? 'text-[var(--bearish)]' : 'text-[var(--muted-foreground)]'
}

function equityBarHeight(equity: number): number {
  if (!result.value?.equityCurve?.length) return 0
  const values = result.value.equityCurve.map((p: { equity: number }) => p.equity)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  return ((equity - min) / range) * 100
}
</script>

<template>
  <div class="space-y-5">
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Backtest
    </h2>

    <!-- Form -->
    <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 sm:px-5 space-y-4 transition-colors duration-200 hover:border-[var(--surface-border-hover)] anim-in anim-delay-1">
      <!-- Instruments -->
      <div>
        <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-2">Instruments</div>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="inst in INSTRUMENTS" :key="inst"
            @click="toggleInstrument(inst)"
            class="px-3 py-1.5 sm:px-2.5 sm:py-1 rounded-lg text-[10px] font-medium transition-all duration-150 active:scale-95"
            :class="form.instruments.includes(inst)
              ? 'bg-[var(--badge-buy)] text-[var(--bullish)] border border-[var(--border-buy)]'
              : 'bg-[var(--surface-skeleton)] text-[var(--muted-foreground)] border border-transparent hover:border-[var(--surface-border)]'"
          >
            {{ inst }}
          </button>
        </div>
      </div>

      <!-- Strategies -->
      <div>
        <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-2">Strategies</div>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="s in STRATEGIES" :key="s"
            @click="toggleStrategy(s)"
            class="px-3 py-1.5 sm:px-2.5 sm:py-1 rounded-lg text-[10px] font-medium transition-all duration-150 active:scale-95"
            :class="form.strategies.includes(s)
              ? 'bg-[var(--badge-buy)] text-[var(--bullish)] border border-[var(--border-buy)]'
              : 'bg-[var(--surface-skeleton)] text-[var(--muted-foreground)] border border-transparent hover:border-[var(--surface-border)]'"
          >
            {{ strategyLabels[s] || s }}
          </button>
        </div>
      </div>

      <!-- Date range + timeframe -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1 block">Start Date</label>
          <input
            v-model="form.startDate" type="date"
            class="w-full px-3 py-1.5 rounded-lg text-xs bg-[var(--surface)] border border-[var(--surface-border)] text-[var(--foreground)] focus:border-[var(--surface-border-hover)] focus:outline-none transition-colors"
          />
        </div>
        <div>
          <label class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1 block">End Date</label>
          <input
            v-model="form.endDate" type="date"
            class="w-full px-3 py-1.5 rounded-lg text-xs bg-[var(--surface)] border border-[var(--surface-border)] text-[var(--foreground)] focus:border-[var(--surface-border-hover)] focus:outline-none transition-colors"
          />
        </div>
        <div>
          <label class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1 block">Timeframe</label>
          <select
            v-model="form.timeframe"
            class="w-full px-3 py-1.5 rounded-lg text-xs bg-[var(--surface)] border border-[var(--surface-border)] text-[var(--foreground)] focus:border-[var(--surface-border-hover)] focus:outline-none transition-colors"
          >
            <option value="1h">1H</option>
            <option value="1d">1D</option>
          </select>
        </div>
      </div>

      <!-- Run button -->
      <div class="flex items-center gap-3">
        <button
          @click="handleRun"
          :disabled="loading"
          class="px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95"
          :class="loading
            ? 'bg-[var(--surface-skeleton)] text-[var(--muted-foreground)] cursor-wait'
            : 'bg-[var(--accent-warm)] text-[var(--primary-foreground)] hover:opacity-90'"
        >
          {{ loading ? 'Running...' : 'Run Backtest' }}
        </button>
        <span v-if="loading" class="text-[10px] text-[var(--muted-foreground)]">This may take a moment...</span>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[var(--border-sell)]">
      {{ error }}
    </div>

    <!-- Results -->
    <TransitionGroup name="results" tag="div" class="space-y-5">
      <template v-if="result">
        <!-- Metrics grid -->
        <div key="metrics" class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 0ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Win Rate</div>
            <div class="text-lg font-bold tabular-nums" :class="pnlClass(result.metrics.winRate - 0.5)">{{ fmtPct(result.metrics.winRate) }}</div>
          </div>
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 50ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Profit Factor</div>
            <div class="text-lg font-bold tabular-nums" :class="result.metrics.profitFactor >= 1.5 ? 'text-[var(--bullish)]' : 'text-[var(--accent-warm)]'">{{ result.metrics.profitFactor.toFixed(2) }}</div>
          </div>
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 100ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Sharpe Ratio</div>
            <div class="text-lg font-bold tabular-nums">{{ result.metrics.sharpeRatio.toFixed(2) }}</div>
          </div>
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 150ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Max Drawdown</div>
            <div class="text-lg font-bold tabular-nums text-[var(--bearish)]">{{ result.metrics.maxDrawdownPct.toFixed(1) }}%</div>
          </div>
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 200ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Expectancy</div>
            <div class="text-lg font-bold tabular-nums" :class="pnlClass(result.metrics.expectancy)">{{ fmtPips(result.metrics.expectancy) }}</div>
          </div>
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 250ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Trades/Day</div>
            <div class="text-lg font-bold tabular-nums">{{ result.metrics.tradesPerDay.toFixed(2) }}</div>
          </div>
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 300ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Total PnL</div>
            <div class="text-lg font-bold tabular-nums" :class="pnlClass(result.metrics.totalPnlPips)">{{ fmtPips(result.metrics.totalPnlPips) }} pips</div>
          </div>
          <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-3 anim-in" style="animation-delay: 350ms">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-1">Total Trades</div>
            <div class="text-lg font-bold tabular-nums">{{ result.metrics.totalTrades }}</div>
          </div>
        </div>

        <!-- Equity curve (simple CSS chart) -->
        <div v-if="result.equityCurve?.length" key="equity" class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-5 py-4 anim-in" style="animation-delay: 400ms">
          <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mb-3">Equity Curve</div>
          <div class="relative h-40">
            <div class="absolute inset-0 flex items-end gap-px">
              <div
                v-for="(point, i) in result.equityCurve"
                :key="i"
                class="flex-1 rounded-t-sm equity-bar"
                :style="{
                  height: equityBarHeight(point.equity) + '%',
                  background: point.equity >= (result.equityCurve[0]?.equity ?? 0) ? 'var(--bullish)' : 'var(--bearish)',
                  '--bar-delay': i * 8 + 'ms',
                }"
                :title="`${point.date}: ${point.equity.toFixed(0)}`"
              />
            </div>
          </div>
          <div class="flex justify-between text-[9px] text-[var(--muted-foreground)] mt-1">
            <span>{{ result.equityCurve[0]?.date }}</span>
            <span>{{ result.equityCurve[result.equityCurve.length - 1]?.date }}</span>
          </div>
        </div>

        <!-- Trade list -->
        <div v-if="result.trades?.length" key="trades" class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] overflow-hidden anim-in" style="animation-delay: 500ms">
          <div class="px-5 py-3 border-b border-[var(--separator)]">
            <div class="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Trades ({{ result.trades.length }})</div>
          </div>
          <div class="overflow-x-auto max-h-72 overflow-y-auto">
            <table class="w-full min-w-[600px] sm:min-w-[700px] text-xs">
              <thead>
                <tr class="border-b border-[var(--table-header-border)]">
                  <th class="text-left text-[10px] text-[var(--muted-foreground)] font-medium py-2 px-5">Instrument</th>
                  <th class="text-left text-[10px] text-[var(--muted-foreground)] font-medium py-2">Strategy</th>
                  <th class="text-left text-[10px] text-[var(--muted-foreground)] font-medium py-2">Dir</th>
                  <th class="text-right text-[10px] text-[var(--muted-foreground)] font-medium py-2">Entry</th>
                  <th class="text-right text-[10px] text-[var(--muted-foreground)] font-medium py-2">Exit</th>
                  <th class="text-right text-[10px] text-[var(--muted-foreground)] font-medium py-2">PnL</th>
                  <th class="text-left text-[10px] text-[var(--muted-foreground)] font-medium py-2 px-5">Reason</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(trade, i) in result.trades"
                  :key="i"
                  class="border-b border-[var(--table-row-border)] hover:bg-[var(--row-hover)] transition-colors"
                >
                  <td class="py-2 px-5 font-medium">{{ trade.instrument }}</td>
                  <td class="py-2 text-[var(--muted-foreground)]">{{ strategyLabels[trade.strategy] || trade.strategy }}</td>
                  <td class="py-2">
                    <span
                      class="inline-flex items-center justify-center w-4 h-4 rounded text-[8px] font-bold uppercase"
                      :class="trade.direction === 'BUY' ? 'bg-[var(--badge-buy)] text-[var(--bullish)]' : 'bg-[var(--badge-sell)] text-[var(--bearish)]'"
                    >{{ trade.direction === 'BUY' ? 'B' : 'S' }}</span>
                  </td>
                  <td class="py-2 text-right tabular-nums">{{ trade.entryPrice.toFixed(trade.instrument.includes('BTC') ? 0 : trade.instrument.includes('JPY') ? 2 : 4) }}</td>
                  <td class="py-2 text-right tabular-nums">{{ trade.exitPrice.toFixed(trade.instrument.includes('BTC') ? 0 : trade.instrument.includes('JPY') ? 2 : 4) }}</td>
                  <td class="py-2 text-right tabular-nums font-semibold" :class="pnlClass(trade.pnl)">{{ fmtPips(trade.pips) }}</td>
                  <td class="py-2 px-5 text-[var(--muted-foreground)]">{{ trade.exitReason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </TransitionGroup>
  </div>
</template>
