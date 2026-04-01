<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { useHeatmap, TIMEFRAMES } from '@/composables/useHeatmap'

const { instruments, pending, error } = useHeatmap()
const timeframes = TIMEFRAMES

function scoreBg(score: number): string {
  switch (score) {
    case 2: return 'bg-[var(--score-strong-bull)] text-[var(--bullish)]'
    case 1: return 'bg-[var(--score-bull)] text-[var(--bullish)]'
    case 0: return 'bg-[var(--score-neutral)] text-[var(--muted-foreground)]'
    case -1: return 'bg-[var(--score-bear)] text-[var(--bearish)]'
    case -2: return 'bg-[var(--score-strong-bear)] text-[var(--bearish)]'
    default: return ''
  }
}

function biasClass(bias: string): string {
  switch (bias) {
    case 'Very Bullish': return 'bg-[var(--bullish-muted)] text-[var(--bullish)]'
    case 'Bullish': return 'bg-[var(--bullish-muted)]/60 text-[var(--bullish)]'
    case 'Neutral': return 'bg-[var(--muted)] text-[var(--muted-foreground)]'
    case 'Bearish': return 'bg-[var(--bearish-muted)]/60 text-[var(--bearish)]'
    case 'Very Bearish': return 'bg-[var(--bearish-muted)] text-[var(--bearish)]'
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
      Multi-Timeframe Scoring — Macro to Intraday Alignment
    </h2>

    <div v-if="error" class="text-[var(--destructive)] text-xs p-4 rounded-lg border border-[var(--destructive)]/20 bg-[var(--destructive)]/5 mb-4">
      Failed to load heatmap data. Retrying...
    </div>

    <Card class="shadow-none py-3">
      <CardContent class="px-3 md:px-5 -mx-1">
        <!-- Skeleton -->
        <div v-if="pending" class="space-y-3">
          <div v-for="i in 8" :key="i" class="flex items-center gap-2">
            <Skeleton class="h-8 w-20" />
            <Skeleton v-for="j in 5" :key="j" class="h-9 w-9 rounded-md" />
            <Skeleton class="h-8 w-10" />
            <Skeleton class="h-7 w-20 rounded-md" />
          </div>
        </div>

        <div v-else class="overflow-x-auto -mx-3 md:mx-0 relative -z-10">
        <Table class="min-w-[640px]">
          <TableHeader>
            <TableRow class="hover:bg-transparent border-[var(--border)]">
              <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Instrument</TableHead>
              <TableHead
                v-for="tf in timeframes"
                :key="tf"
                class="text-[10px] text-[var(--muted-foreground)] h-7 text-center w-16"
              >
                {{ tf }}
              </TableHead>
              <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 text-center w-16">Total</TableHead>
              <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 text-center w-28">Bias</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="row in instruments"
              :key="row.instrument"
              class="border-[var(--border)]/40"
            >
              <TableCell class="font-medium text-sm py-2.5">
                {{ row.instrument }}
                <span v-if="row.wait" class="ml-1.5 text-[10px] font-medium text-[var(--accent-warm)]">WAIT</span>
              </TableCell>
              <TableCell
                v-for="tf in timeframes"
                :key="tf"
                class="py-2.5 text-center"
              >
                <span
                  v-if="!isAllZero(row)"
                  class="inline-flex items-center justify-center w-9 h-9 rounded-md text-xs font-semibold tabular-nums"
                  :class="scoreBg(row.scores[tf])"
                >
                  {{ row.scores[tf] > 0 ? '+' : '' }}{{ row.scores[tf] }}
                </span>
                <span
                  v-else
                  class="inline-flex items-center justify-center w-9 h-9 rounded-md text-xs text-[var(--muted-foreground)]"
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
              <TableCell class="py-2.5 text-center">
                <span
                  v-if="!isAllZero(row)"
                  class="inline-flex items-center justify-center px-3 py-1 rounded-md text-[10px] font-semibold tracking-wide"
                  :class="biasClass(row.bias)"
                >
                  {{ row.bias }}
                </span>
                <span
                  v-else
                  class="inline-flex items-center justify-center px-3 py-1 rounded-md text-[10px] text-[var(--muted-foreground)] bg-[var(--muted)]"
                >
                  No data
                </span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        </div>
      </CardContent>
    </Card>
  </section>
</template>
