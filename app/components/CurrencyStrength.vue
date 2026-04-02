<script setup lang="ts">
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useYieldSpread } from '@/composables/useYieldSpread'

const { buyCandidates, sellCandidates, maxSpread, pending, error } = useYieldSpread()

function fmtSpread(v: number) {
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
}

function fmtDelta(v: number) {
  return (v >= 0 ? '+' : '') + v.toFixed(2)
}
</script>

<template>
  <section>
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-4 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Currency Strength — 2Y Yield Spread
    </h2>

    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[rgba(239,68,68,0.15)]">
      Failed to load yield spread data. Retrying...
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Buy Candidates -->
      <div class="border border-[rgba(255,255,255,0.07)] rounded-xl bg-[rgba(7,7,13,0.5)] py-4 overflow-hidden transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]">
        <div class="px-5">
          <div class="text-[11px] font-semibold tracking-wider uppercase text-gradient-bullish mb-3">
            Buy Candidates
          </div>

          <Table v-if="!pending">
            <TableHeader>
              <TableRow class="hover:bg-transparent border-[rgba(255,255,255,0.05)]">
                <TableHead class="w-6 text-[10px] text-[var(--muted-foreground)] h-7">#</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Pair</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Spread</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-28" />
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">&Delta;W</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-10">MA20</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="p in buyCandidates"
                :key="p.pair"
                class="border-[rgba(255,255,255,0.03)] transition-colors duration-200 hover:bg-[rgba(255,255,255,0.03)]"
              >
                <TableCell class="tabular-nums text-[var(--muted-foreground)] text-xs py-2.5">{{ p.rank }}</TableCell>
                <TableCell class="font-medium text-sm py-2.5">{{ p.pair }}</TableCell>
                <TableCell class="tabular-nums font-semibold text-sm py-2.5 text-[var(--bullish)]">{{ fmtSpread(p.spread) }}</TableCell>
                <TableCell class="py-2.5">
                  <div class="w-full h-1.5 rounded-full overflow-hidden bg-[rgba(255,255,255,0.04)]">
                    <div
                      class="h-full rounded-full transition-all duration-500"
                      style="background: linear-gradient(90deg, #10b981, #34d399);"
                      :style="{ width: (p.spread / maxSpread * 100) + '%', opacity: 0.7 }"
                    />
                  </div>
                </TableCell>
                <TableCell
                  class="tabular-nums text-xs py-2.5"
                  :class="p.weeklyDelta >= 0 ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'"
                >
                  {{ fmtDelta(p.weeklyDelta) }}
                </TableCell>
                <TableCell class="py-2.5">
                  <span
                    v-if="p.ma20Above !== null"
                    class="text-xs"
                    :class="p.ma20Above ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'"
                  >
                    {{ p.ma20Above ? '▲' : '▼' }}
                  </span>
                  <span v-else class="text-xs text-[var(--muted-foreground)]">—</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <div v-else class="space-y-3 pt-2">
            <div v-for="i in 5" :key="i" class="flex items-center gap-3">
              <div class="h-4 w-4 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-16 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-14 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 flex-1 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-10 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-6 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
            </div>
          </div>
        </div>
      </div>

      <!-- Sell Candidates -->
      <div class="border border-[rgba(255,255,255,0.07)] rounded-xl bg-[rgba(7,7,13,0.5)] py-4 overflow-hidden transition-colors duration-200 hover:border-[rgba(255,255,255,0.12)]">
        <div class="px-5">
          <div class="text-[11px] font-semibold tracking-wider uppercase text-gradient-bearish mb-3">
            Sell Candidates
          </div>

          <Table v-if="!pending">
            <TableHeader>
              <TableRow class="hover:bg-transparent border-[rgba(255,255,255,0.05)]">
                <TableHead class="w-6 text-[10px] text-[var(--muted-foreground)] h-7">#</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Pair</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Spread</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-28" />
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">&Delta;W</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-10">MA20</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="p in sellCandidates"
                :key="p.pair"
                class="border-[rgba(255,255,255,0.03)] transition-colors duration-200 hover:bg-[rgba(255,255,255,0.03)]"
              >
                <TableCell class="tabular-nums text-[var(--muted-foreground)] text-xs py-2.5">{{ p.rank }}</TableCell>
                <TableCell class="font-medium text-sm py-2.5">{{ p.pair }}</TableCell>
                <TableCell class="tabular-nums font-semibold text-sm py-2.5 text-[var(--bearish)]">{{ fmtSpread(p.spread) }}</TableCell>
                <TableCell class="py-2.5">
                  <div class="w-full h-1.5 rounded-full overflow-hidden bg-[rgba(255,255,255,0.04)]">
                    <div
                      class="h-full rounded-full transition-all duration-500"
                      style="background: linear-gradient(90deg, #ef4444, #f87171);"
                      :style="{ width: (Math.abs(p.spread) / maxSpread * 100) + '%', opacity: 0.7 }"
                    />
                  </div>
                </TableCell>
                <TableCell
                  class="tabular-nums text-xs py-2.5"
                  :class="p.weeklyDelta >= 0 ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'"
                >
                  {{ fmtDelta(p.weeklyDelta) }}
                </TableCell>
                <TableCell class="py-2.5">
                  <span
                    v-if="p.ma20Above !== null"
                    class="text-xs"
                    :class="p.ma20Above ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'"
                  >
                    {{ p.ma20Above ? '▲' : '▼' }}
                  </span>
                  <span v-else class="text-xs text-[var(--muted-foreground)]">—</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <div v-else class="space-y-3 pt-2">
            <div v-for="i in 5" :key="i" class="flex items-center gap-3">
              <div class="h-4 w-4 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-16 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-14 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 flex-1 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-10 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
              <div class="h-4 w-6 rounded bg-[rgba(255,255,255,0.04)] shimmer" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
