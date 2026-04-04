<script setup lang="ts">
import { useSignalHistory } from '~/composables/useSignalHistory'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'

const {
  filteredSignals,
  stats,
  pending,
  error,
  instrumentFilter,
  strategyFilter,
  outcomeFilter,
  updateSignal,
  debouncedSaveNotes,
  relativeTime,
} = useSignalHistory()

const expanded = ref<Set<string>>(new Set())

function toggle(id: string) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
}

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

const instruments = ['XAUUSD', 'XAGUSD', 'USDJPY', 'GBPJPY', 'BTCUSD']
const strategies = ['confluence_breakout', 'mean_reversion', 'momentum_shift']
const outcomes: Array<{ value: string; label: string }> = [
  { value: 'PENDING', label: 'Pending' },
  { value: 'WIN', label: 'Win' },
  { value: 'LOSS', label: 'Loss' },
  { value: 'EXPIRED_TIME', label: 'Expired (Time)' },
  { value: 'EXPIRED_ADVERSE', label: 'Expired (Adverse)' },
]

function outcomeColor(outcome: string) {
  switch (outcome) {
    case 'WIN': return 'text-[var(--bullish)] bg-[var(--badge-buy)]'
    case 'LOSS': return 'text-[var(--bearish)] bg-[var(--badge-sell)]'
    case 'EXPIRED_ADVERSE': return 'text-[var(--bearish)] bg-[rgba(239,68,68,0.15)]'
    case 'PENDING': return 'text-[var(--accent-warm)] bg-[var(--accent-warm-muted)]'
    case 'EXPIRED_TIME':
    case 'EXPIRED':
    default: return 'text-[var(--muted-foreground)] bg-[var(--surface-skeleton)]'
  }
}

function borderClass(outcome: string) {
  switch (outcome) {
    case 'WIN': return 'border-l-[var(--bullish)]'
    case 'LOSS': return 'border-l-[var(--bearish)]'
    case 'EXPIRED_ADVERSE': return 'border-l-[var(--bearish)]'
    case 'PENDING': return 'border-l-[var(--accent-warm)]'
    default: return 'border-l-[var(--muted-foreground)]'
  }
}

function statusBadge(status: string) {
  if (status === 'taken') return { label: 'Took It', class: 'text-[var(--bullish)] bg-[var(--badge-buy)]' }
  if (status === 'skipped') return { label: 'Skipped', class: 'text-[var(--muted-foreground)] bg-[var(--surface-skeleton)]' }
  return null
}

function formatExitReason(reason: string): string {
  switch (reason) {
    case 'TAKE_PROFIT': return 'Take Profit'
    case 'STOP_LOSS': return 'Stop Loss'
    case 'EXPIRED_TIME': return 'Expired (Time)'
    case 'EXPIRED_ADVERSE': return 'Expired (Adverse Drift)'
    default: return reason
  }
}

const notesDrafts = ref<Record<string, string>>({})

function getNotes(signal: { id: string; notes: string }) {
  return notesDrafts.value[signal.id] ?? signal.notes
}

function setNotes(signal: { id: string; notes: string }, val: string) {
  if (val.length > 500) return
  notesDrafts.value[signal.id] = val
  debouncedSaveNotes(signal.id, val)
}

function markTaken(signal: { id: string }) {
  updateSignal(signal.id, { userStatus: 'taken' })
}

function markSkipped(signal: { id: string }) {
  updateSignal(signal.id, { userStatus: 'skipped' })
}
</script>

<template>
  <section>
    <!-- Error state -->
    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[var(--border-sell)]">
      {{ error }}
    </div>

    <template v-else>
      <!-- Filter bar -->
      <div class="flex flex-wrap items-center gap-2 mb-4">
        <!-- Instrument -->
        <select
          v-model="instrumentFilter"
          class="h-8 px-2.5 rounded-lg text-[10px] font-medium bg-[var(--surface)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none focus:border-[var(--surface-border-hover)] transition-colors"
        >
          <option value="all">All Instruments</option>
          <option v-for="inst in instruments" :key="inst" :value="inst">{{ inst }}</option>
        </select>

        <!-- Strategy -->
        <select
          v-model="strategyFilter"
          class="h-8 px-2.5 rounded-lg text-[10px] font-medium bg-[var(--surface)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none focus:border-[var(--surface-border-hover)] transition-colors"
        >
          <option value="all">All Strategies</option>
          <option v-for="strat in strategies" :key="strat" :value="strat">{{ strategyLabel[strat] || strat }}</option>
        </select>

        <!-- Outcome -->
        <select
          v-model="outcomeFilter"
          class="h-8 px-2.5 rounded-lg text-[10px] font-medium bg-[var(--surface)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none focus:border-[var(--surface-border-hover)] transition-colors"
        >
          <option value="all">All Outcomes</option>
          <option v-for="o in outcomes" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>

        <!-- Count -->
        <span class="text-[10px] text-[var(--muted-foreground)] ml-auto">
          Showing {{ filteredSignals.length }} of {{ stats.total }} signals
        </span>
      </div>

      <!-- Loading skeleton -->
      <template v-if="pending">
        <div v-for="i in 3" :key="i" class="h-[104px] rounded-xl shimmer border border-[var(--surface-skeleton)] mb-2" />
      </template>

      <!-- Empty state -->
      <template v-else-if="!filteredSignals.length">
        <div class="text-[var(--muted-foreground)] text-xs p-8 rounded-xl border border-[var(--surface-border)] text-center">
          <p class="mb-1">No signals tracked yet</p>
          <p class="text-[10px] opacity-60">Signals will appear here once the engine generates them</p>
        </div>
      </template>

      <!-- Signal cards -->
      <div v-else class="space-y-2">
        <div
          v-for="signal in filteredSignals"
          :key="signal.id"
          class="border rounded-xl bg-[var(--surface)] overflow-hidden transition-colors duration-200 hover:border-[var(--surface-border-hover)] border-l-2"
          :class="borderClass(signal.outcome)"
        >
          <!-- Header row -->
          <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--separator)]">
            <div class="flex items-center gap-2 min-w-0">
              <!-- Direction badge -->
              <span
                class="inline-flex items-center justify-center w-5 h-5 rounded text-[9px] font-bold uppercase flex-shrink-0"
                :class="signal.direction === 'BUY'
                  ? 'bg-[var(--badge-buy)] text-[var(--bullish)]'
                  : 'bg-[var(--badge-sell)] text-[var(--bearish)]'"
              >
                {{ signal.direction === 'BUY' ? 'B' : 'S' }}
              </span>
              <span class="text-sm font-semibold">{{ signal.instrument }}</span>
              <!-- Strategy badge -->
              <span class="text-[9px] px-1.5 py-0.5 rounded bg-[var(--accent-warm-muted)] text-[var(--accent-warm)]">
                {{ strategyLabel[signal.strategy] || signal.strategy }}
              </span>
              <span class="text-[10px] text-[var(--muted-foreground)]">{{ signal.timeframe }}</span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <!-- Outcome badge -->
              <span class="text-[9px] px-1.5 py-0.5 rounded-full font-medium" :class="outcomeColor(signal.outcome)">
                <template v-if="signal.outcome === 'WIN'">WIN {{ signal.pnlPips ? `+${signal.pnlPips.toFixed(1)}` : '' }}</template>
                <template v-else-if="signal.outcome === 'LOSS'">LOSS {{ signal.pnlPips ? signal.pnlPips.toFixed(1) : '' }}</template>
                <template v-else-if="signal.outcome === 'PENDING'">PENDING</template>
                <template v-else-if="signal.outcome === 'EXPIRED_ADVERSE'">EXPIRED (Drift)</template>
                <template v-else-if="signal.outcome === 'EXPIRED_TIME'">EXPIRED (Time)</template>
                <template v-else>EXPIRED</template>
              </span>
              <!-- User status badge -->
              <span v-if="statusBadge(signal.userStatus)" class="text-[9px] px-1.5 py-0.5 rounded-full font-medium" :class="statusBadge(signal.userStatus)!.class">
                {{ statusBadge(signal.userStatus)!.label }}
              </span>
              <!-- Confidence -->
              <span
                class="text-sm font-bold tabular-nums"
                :class="signal.confidence >= 80 ? 'text-[var(--bullish)]' : signal.confidence >= 60 ? 'text-[var(--accent-warm)]' : 'text-[var(--muted-foreground)]'"
              >
                {{ signal.confidence }}%
              </span>
            </div>
          </div>

          <!-- Metrics row -->
          <div class="px-4 py-2.5">
            <div class="flex items-center gap-4 text-xs">
              <span class="flex items-center gap-1">
                <span class="text-[var(--muted-foreground)]">Entry</span>
                <span class="tabular-nums font-medium">{{ fmtPrice(signal.instrument, signal.entry) }}</span>
              </span>
              <span class="text-[var(--separator)]">→</span>
              <span class="flex items-center gap-1">
                <span class="text-[var(--muted-foreground)]">SL</span>
                <span class="tabular-nums font-medium text-[var(--bearish)]">{{ fmtPrice(signal.instrument, signal.stopLoss) }}</span>
              </span>
              <span class="text-[var(--separator)]">→</span>
              <span class="flex items-center gap-1">
                <span class="text-[var(--muted-foreground)]">TP</span>
                <span class="tabular-nums font-medium text-[var(--bullish)]">{{ fmtPrice(signal.instrument, signal.takeProfit) }}</span>
              </span>
              <span class="text-[var(--muted-foreground)] text-[10px] tabular-nums">R:R {{ signal.riskReward }}:1</span>
              <span v-if="signal.pnlPips !== null" class="tabular-nums font-medium text-[10px]" :class="signal.pnlPips >= 0 ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'">
                {{ signal.pnlPips >= 0 ? '+' : '' }}{{ signal.pnlPips.toFixed(1) }} pips
              </span>
              <span class="ml-auto text-[10px] text-[var(--muted-foreground)]">{{ relativeTime(signal.generatedAt) }}</span>
            </div>

            <!-- Expand toggle -->
            <button
              class="flex items-center gap-1 mt-2 text-[9px] text-[var(--accent-warm)] hover:underline"
              @click="toggle(signal.id)"
            >
              <component :is="expanded.has(signal.id) ? ChevronDown : ChevronRight" class="w-3 h-3" />
              {{ expanded.has(signal.id) ? 'Hide details' : 'Show details' }}
            </button>
          </div>

          <!-- Expanded details -->
          <div v-if="expanded.has(signal.id)" class="px-4 pb-3 border-t border-[var(--separator)] pt-3">
            <!-- Reasons -->
            <div v-if="signal.reasons?.length" class="mb-3">
              <p class="text-[9px] text-[var(--muted-foreground)] uppercase tracking-wide mb-1.5">Reasons</p>
              <ul class="space-y-0.5">
                <li
                  v-for="(r, i) in signal.reasons"
                  :key="i"
                  class="text-[10px] text-[var(--muted-foreground)] pl-2 border-l border-[var(--separator)]"
                >
                  {{ r }}
                </li>
              </ul>
            </div>

            <!-- Exit reason -->
            <div v-if="signal.exitReason" class="mb-3">
              <p class="text-[9px] text-[var(--muted-foreground)] uppercase tracking-wide mb-1">Exit</p>
              <div class="flex items-center gap-2 text-[10px]">
                <span
                  class="px-1.5 py-0.5 rounded font-medium"
                  :class="signal.exitReason === 'TAKE_PROFIT'
                    ? 'text-[var(--bullish)] bg-[var(--badge-buy)]'
                    : signal.exitReason === 'STOP_LOSS'
                      ? 'text-[var(--bearish)] bg-[var(--badge-sell)]'
                      : signal.exitReason === 'EXPIRED_ADVERSE'
                        ? 'text-[var(--bearish)] bg-[rgba(239,68,68,0.15)]'
                        : 'text-[var(--muted-foreground)] bg-[var(--surface-skeleton)]'"
                >
                  {{ formatExitReason(signal.exitReason) }}
                </span>
                <span v-if="signal.exitPrice" class="text-[var(--muted-foreground)]">
                  @ {{ fmtPrice(signal.instrument, signal.exitPrice) }}
                </span>
                <span v-if="signal.exitTime" class="text-[var(--muted-foreground)]">
                  {{ relativeTime(signal.exitTime) }}
                </span>
              </div>
            </div>

            <!-- Action buttons (PENDING only) -->
            <div v-if="signal.outcome === 'PENDING'" class="flex items-center gap-2 mb-3">
              <button
                class="h-7 px-3 rounded-lg text-[10px] font-medium bg-[var(--badge-buy)] text-[var(--bullish)] border border-[var(--border-buy)] hover:bg-[rgba(16,185,129,0.2)] transition-colors"
                @click="markTaken(signal)"
              >
                Took It
              </button>
              <button
                class="h-7 px-3 rounded-lg text-[10px] font-medium bg-[var(--surface-skeleton)] text-[var(--muted-foreground)] border border-[var(--surface-border)] hover:border-[var(--surface-border-hover)] transition-colors"
                @click="markSkipped(signal)"
              >
                Skipped
              </button>
            </div>

            <!-- Notes -->
            <div>
              <textarea
                :value="getNotes(signal)"
                @input="setNotes(signal, ($event.target as HTMLTextAreaElement).value)"
                placeholder="Add notes about this signal..."
                rows="2"
                class="w-full px-3 py-2 rounded-lg text-[10px] bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] outline-none focus:border-[var(--surface-border-hover)] resize-none transition-colors"
              />
              <div class="flex justify-end mt-0.5">
                <span class="text-[9px] text-[var(--muted-foreground)] tabular-nums">
                  {{ (notesDrafts[signal.id] ?? signal.notes).length }}/500
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
