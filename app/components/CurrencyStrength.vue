<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
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
      Currency Strength — 2Y Bond Yield Spread
    </h2>

    <div v-if="error" class="text-[var(--destructive)] text-xs p-4 rounded-lg border border-[var(--destructive)]/20 bg-[var(--destructive)]/5">
      Failed to load yield spread data. Retrying...
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <!-- Buy Candidates -->
      <Card class="shadow-none py-3 gap-1">
        <CardHeader class="px-5 pb-0 pt-0">
          <CardTitle class="text-[11px] font-semibold tracking-wider uppercase text-[var(--foreground)]">
            Buy Candidates
          </CardTitle>
        </CardHeader>
        <CardContent class="px-5">
          <Table v-if="!pending">
            <TableHeader>
              <TableRow class="hover:bg-transparent border-[var(--border)]">
                <TableHead class="w-6 text-[10px] text-[var(--muted-foreground)] h-7">#</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Pair</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Spread</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-28"></TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">&Delta;W</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-10">MA20</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="p in buyCandidates"
                :key="p.pair"
                class="border-[var(--border)]/40"
              >
                <TableCell class="tabular-nums text-[var(--muted-foreground)] text-xs py-2.5">{{ p.rank }}</TableCell>
                <TableCell class="font-medium text-sm py-2.5">{{ p.pair }}</TableCell>
                <TableCell class="tabular-nums font-semibold text-sm py-2.5 text-[var(--bullish)]">{{ fmtSpread(p.spread) }}</TableCell>
                <TableCell class="py-2.5">
                  <div class="w-full h-1.5 rounded-full overflow-hidden" style="background: oklch(0.21 0.018 60)">
                    <div
                      class="h-full bg-[var(--bullish)] rounded-full opacity-70"
                      :style="{ width: (p.spread / maxSpread * 100) + '%' }"
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
              <Skeleton class="h-4 w-4" />
              <Skeleton class="h-4 w-16" />
              <Skeleton class="h-4 w-14" />
              <Skeleton class="h-4 flex-1" />
              <Skeleton class="h-4 w-10" />
              <Skeleton class="h-4 w-6" />
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Sell Candidates -->
      <Card class="shadow-none py-3 gap-1">
        <CardHeader class="px-5 pb-0 pt-0">
          <CardTitle class="text-[11px] font-semibold tracking-wider uppercase text-[var(--foreground)]">
            Sell Candidates
          </CardTitle>
        </CardHeader>
        <CardContent class="px-5">
          <Table v-if="!pending">
            <TableHeader>
              <TableRow class="hover:bg-transparent border-[var(--border)]">
                <TableHead class="w-6 text-[10px] text-[var(--muted-foreground)] h-7">#</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Pair</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">Spread</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-28"></TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7">&Delta;W</TableHead>
                <TableHead class="text-[10px] text-[var(--muted-foreground)] h-7 w-10">MA20</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="p in sellCandidates"
                :key="p.pair"
                class="border-[var(--border)]/40"
              >
                <TableCell class="tabular-nums text-[var(--muted-foreground)] text-xs py-2.5">{{ p.rank }}</TableCell>
                <TableCell class="font-medium text-sm py-2.5">{{ p.pair }}</TableCell>
                <TableCell class="tabular-nums font-semibold text-sm py-2.5 text-[var(--bearish)]">{{ fmtSpread(p.spread) }}</TableCell>
                <TableCell class="py-2.5">
                  <div class="w-full h-1.5 rounded-full overflow-hidden" style="background: oklch(0.21 0.018 60)">
                    <div
                      class="h-full bg-[var(--bearish)] rounded-full opacity-70"
                      :style="{ width: (Math.abs(p.spread) / maxSpread * 100) + '%' }"
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
              <Skeleton class="h-4 w-4" />
              <Skeleton class="h-4 w-16" />
              <Skeleton class="h-4 w-14" />
              <Skeleton class="h-4 flex-1" />
              <Skeleton class="h-4 w-10" />
              <Skeleton class="h-4 w-6" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </section>
</template>
