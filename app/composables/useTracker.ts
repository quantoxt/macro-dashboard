export interface TrackedSignal {
  id: string
  instrument: string
  direction: 'BUY' | 'SELL'
  confidence: number
  entry: number
  stopLoss: number
  takeProfit: number
  riskReward: number
  strategy: string
  timeframe: string
  reasons: string[]
  generatedAt: string
  outcome: 'WIN' | 'LOSS' | 'EXPIRED' | null
  exitPrice: number | null
  exitReason: string | null
  pnlPips: number | null
  maxFavorable: number | null
  maxAdverse: number | null
  exitTime: string | null
}

export interface TrackerStats {
  total: number
  wins: number
  losses: number
  expired: number
  pending: number
  winRate: number
  totalPnlPips: number
}

export interface StrategyPerformance {
  total: number
  wins: number
  losses: number
  expired: number
  pending: number
  winRate: number
  avgPnlPips: number
  totalPnlPips: number
  avgDurationHours: number
  bestTrade: number
  worstTrade: number
}

export interface PerformanceData {
  strategies: Record<string, StrategyPerformance>
  overall: {
    total: number
    wins: number
    losses: number
    expired: number
    pending: number
    winRate: number
    totalPnlPips: number
    avgDurationHours: number
  }
  error?: string
}

export function useTracker() {
  const signals = ref<TrackedSignal[]>([])
  const stats = ref<TrackerStats>({ total: 0, wins: 0, losses: 0, expired: 0, pending: 0, winRate: 0, totalPnlPips: 0 })
  const performance = ref<PerformanceData | null>(null)
  const pending = ref(true)
  const error = ref<string | null>(null)
  let intervalId: ReturnType<typeof setInterval> | null = null

  async function fetchSignals() {
    try {
      const res = await $fetch<any>('/api/tracker')
      signals.value = res.signals ?? []
      stats.value = res.stats ?? { total: 0, wins: 0, losses: 0, expired: 0, pending: 0, winRate: 0, totalPnlPips: 0 }
      error.value = res.error ?? null
    }
    catch (err: any) {
      error.value = 'Signal engine unavailable'
    }
    finally {
      pending.value = false
    }
  }

  async function fetchPerformance() {
    try {
      const res = await $fetch<PerformanceData>('/api/tracker-performance')
      performance.value = res
      error.value = res.error ?? null
    }
    catch (err: any) {
      error.value = 'Signal engine unavailable'
    }
  }

  onMounted(() => {
    fetchSignals()
    fetchPerformance()
    intervalId = setInterval(() => {
      fetchSignals()
      fetchPerformance()
    }, 5 * 60 * 1000)
  })

  onScopeDispose(() => {
    if (intervalId) clearInterval(intervalId)
  })

  return { signals, stats, performance, pending, error, fetchSignals, fetchPerformance }
}
