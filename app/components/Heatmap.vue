<script setup lang="ts">
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useHeatmap, TIMEFRAMES } from '@/composables/useHeatmap'

const { instruments, pending, error } = useHeatmap()
const timeframes = TIMEFRAMES

function scoreBg(score: number): string {
  switch (score) {
    case 2: return 'bg-[var(--score-strong-bull)] text-[var(--bullish)] glow-bullish'
    case 1: return 'bg-[var(--score-bull)] text-[var(--bullish)]'
    case 0: return 'bg-[var(--score-neutral)] text-[var(--muted-foreground)]'
    case -1: return 'bg-[var(--score-bear)] text-[var(--bearish)]'
    case -2: return 'bg-[var(--score-strong-bear)] text-[var(--bearish)] glow-bearish'
    default: return ''
  }
}

function biasClass(bias: string): string {
  switch (bias) {
    case 'Very Bullish': return 'bg-[rgba(16,185,129,0.12)] text-[var(--bullish)]'
    case 'Bullish': return 'bg-[rgba(16,185,129,0.08)] text-[var(--bullish)]'
    case 'Neutral': return 'bg-[rgba(255,255,255,0.04)] text-[var(--muted-foreground)]'
    case 'Bearish': return 'bg-[rgba(239,68,68,0.08)] text-[var(--bearish)]'
    case 'Very Bearish': return 'bg-[rgba(239,68,68,0.12)] text-[var(--bearish)]'
    default: return ''
  }
}

function fmtTotal(t: number) {
  return (t >= 0 ? '+' : '') + t
}

function isAllZero(row: { scores: Record<string, number>; total: number }) {
  return row.total === 0 && Object.values(row.scores).every(v => v === 0)
}
</script>

<template>
  <section>
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Multi-Timeframe Scoring
    </h2>

    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[rgba(239,68,68,0.15)]">
      Failed to load heatmap data. Retrying...
    </div>

    <!-- Skeleton -->
    <div v-else-if="pending" class="rounded-xl border border-[rgba(255,255,255,0.07)] bg-[rgba(7,7,13,0.5)] p-5">
      <div class="space-y-3">
        <div v-for="i in 8" :key="i" class="flex items-center gap-2">
          <div class="h-8 w-20 rounded-lg bg-[rgba(255,255,255,0.04)] shimmer" />
          <div v-for="j in 5" :key="j" class="h-9 w-9 rounded-lg bg-[rgba(255,255,255,0.04)] shimmer" />
          <div class="h-8 w-10 rounded-lg bg-[rgba(255,255,255,0.04)] shimmer" />
          <div class="h-7 w-20 rounded-lg bg-[rgba(255,255,255,0.04)] shimmer" />
        </div>
      </div>
    </div>

    <!-- Table -->
    <div
      v-else
      class="border border-[rgba(255,255,255,0.07)] rounded-xl bg-[rgba(7,7,13,0.5)] py-4 overflow-hidden transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]"
    >
      <div class="overflow-x-auto">
        <Table class="min-w-[640px]">
          <TableHeader>
            <TableRow class="hover:bg-transparent border-[rgba(255,255,255,0.05)]">
              <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 pl-5">Instrument</TableHead>
              <TableHead
                v-for="tf in timeframes"
                :key="tf"
                class="text-[10px] text-[var(--muted-foreground)] h-7 text-center w-16"
              >
                {{ tf }}
              </TableHead>
              <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 text-center w-16">Total</TableHead>
              <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 text-center w-28 pr-5">Bias</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="row in instruments"
              :key="row.instrument"
              class="border-[rgba(255,255,255,0.03)] transition-colors duration-200 hover:bg-[rgba(255,255,255,0.03)]"
            >
              <TableCell class="font-medium text-sm py-2.5 pl-5">
                {{ row.instrument }}
                <span v-if="row.wait" class="ml-1.5 text-[10px] font-medium text-[var(--accent-warm)] signal-pulse">WAIT</span>
              </TableCell>
              <TableCell
                v-for="tf in timeframes"
                :key="tf"
                class="py-2.5 text-center"
              >
                <span
                  v-if="!isAllZero(row)"
                  class="inline-flex items-center justify-center w-9 h-9 rounded-lg text-xs font-semibold tabular-nums transition-all duration-200"
                  :class="scoreBg(row.scores[tf])"
                >
                  {{ row.scores[tf] > 0 ? '+' : '' }}{{ row.scores[tf] }}
                </span>
                <span
                  v-else
                  class="inline-flex items-center justify-center w-9 h-9 rounded-lg text-xs text-[var(--muted-foreground)]"
                  title="Insufficient data"
                >
                  —
                </span>
              </TableCell>
              <TableCell
                v-if="!isAllZero(row)"
                class="py-2.5 text-center text-sm font-semibold tabular-nums"
                :class="row.total >= 0 ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'"
              >
                {{ fmtTotal(row.total) }}
              </TableCell>
              <TableCell v-else class="py-2.5 text-center text-sm font-semibold tabular-nums text-[var(--muted-foreground)]">
                —
              </TableCell>
              <TableCell class="py-2.5 text-center pr-5">
                <span
                  v-if="!isAllZero(row)"
                  class="inline-flex items-center justify-center px-3 py-1 rounded-lg text-[10px] font-semibold tracking-wide"
                  :class="biasClass(row.bias)"
                >
                  {{ row.bias }}
                </span>
                <span
                  v-else
                  class="inline-flex items-center justify-center px-3 py-1 rounded-lg text-[10px] text-[var(--muted-foreground)] bg-[rgba(255,255,255,0.03)]"
                >
                  No data
                </span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  </section>
</template>
