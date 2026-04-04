export interface BacktestMetrics {
  totalTrades: number
  winRate: number
  profitFactor: number
  sharpeRatio: number
  maxDrawdownPct: number
  expectancy: number
  avgWinPips: number
  avgLossPips: number
  recoveryFactor: number
  tradesPerDay: number
  totalPnlPips: number
}

export interface EquityPoint {
  date: string
  equity: number
}

export interface BacktestTrade {
  instrument: string
  strategy: string
  direction: string
  entryPrice: number
  exitPrice: number
  stopLoss: number
  takeProfit: number
  pnl: number
  pips: number
  exitReason: string
  durationBars: number
  confidence: number
  entryTime: string
  exitTime: string
}

export interface BacktestResult {
  metrics: BacktestMetrics
  equityCurve: EquityPoint[]
  trades: BacktestTrade[]
}

export interface BacktestParams {
  instruments: string[]
  strategies: string[]
  startDate: string
  endDate: string
  timeframe: string
}

export function useBacktest() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const result = ref<BacktestResult | null>(null)

  async function runBacktest(params: BacktestParams) {
    loading.value = true
    error.value = null
    result.value = null

    try {
      const data = await $fetch<BacktestResult>('/api/backtest', {
        method: 'POST',
        body: params,
      })
      result.value = data
    }
    catch (err: any) {
      error.value = err.data?.statusMessage || err.message || 'Backtest failed'
    }
    finally {
      loading.value = false
    }
  }

  return { loading, error, result, runBacktest }
}
