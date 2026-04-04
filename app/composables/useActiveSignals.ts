export interface ActiveSignal {
  pair: string
  direction: 'buy' | 'sell'
  confidence: number
  entry: number
  tp: number
  sl: number
  reason: string
  reasons: string[]
  timeframe: string
  timestamp: string
  generatedAt: string
  strategy: string
  riskReward: number
}

interface EngineSignal {
  instrument: string
  direction: string
  confidence: number
  entry: number
  stopLoss: number
  takeProfit: number
  riskReward: number
  strategy: string
  timeframe: string
  reasons: string[]
  generatedAt: string
}

interface SignalsResponse {
  signals?: EngineSignal[]
  updatedAt?: string | null
  error?: string
}

function mapSignal(raw: EngineSignal): ActiveSignal {
  const timestamp = raw.generatedAt
    ? new Date(raw.generatedAt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false }) + ' UTC'
    : ''

  return {
    pair: raw.instrument,
    direction: raw.direction.toLowerCase() as 'buy' | 'sell',
    confidence: raw.confidence,
    entry: raw.entry,
    tp: raw.takeProfit,
    sl: raw.stopLoss,
    reason: raw.reasons?.join(' • ') ?? '',
    reasons: raw.reasons ?? [],
    timeframe: raw.timeframe,
    timestamp,
    generatedAt: raw.generatedAt ?? '',
    strategy: raw.strategy,
    riskReward: raw.riskReward,
  }
}

export function useActiveSignals() {
  const signals = ref<ActiveSignal[]>([])
  const pending = ref(true)
  const error = ref<string | null>(null)
  const updatedAt = ref<string | null>(null)
  let intervalId: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    try {
      const res: SignalsResponse = await $fetch('/api/signals')

      if (!res || res.error) {
        error.value = res?.error || 'Failed to load signals'
        signals.value = []
      }
      else {
        const rawSignals = Array.isArray(res.signals) ? res.signals : []
        signals.value = rawSignals.map(mapSignal)
        updatedAt.value = res.updatedAt ?? null
        error.value = null
      }
    }
    catch (err: any) {
      error.value = 'Signal engine unavailable'
      signals.value = []
    }
    finally {
      pending.value = false
    }
  }

  // Only fetch and set interval on client side
  onMounted(() => {
    refresh()
    intervalId = setInterval(refresh, 5 * 60 * 1000)
  })

  onScopeDispose(() => {
    if (intervalId) clearInterval(intervalId)
  })

  return { signals, pending, error, updatedAt, refresh }
}
