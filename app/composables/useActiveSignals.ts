export interface ActiveSignal {
  pair: string
  direction: 'buy' | 'sell'
  confidence: number
  entry: number
  tp: number
  sl: number
  reason: string
  timeframe: string
  timestamp: string
}

const MOCK_SIGNALS: ActiveSignal[] = [
  { pair: 'EUR/USD', direction: 'buy', confidence: 87, entry: 1.0852, tp: 1.0920, sl: 1.0795, reason: 'Yield spread widening, H4 momentum aligned', timeframe: 'H4', timestamp: '14:32 UTC' },
  { pair: 'GBP/JPY', direction: 'buy', confidence: 74, entry: 191.45, tp: 193.10, sl: 190.50, reason: 'Risk-on flow, D1 breakout above resistance', timeframe: 'D1', timestamp: '12:15 UTC' },
  { pair: 'AUD/USD', direction: 'sell', confidence: 82, entry: 0.6523, tp: 0.6460, sl: 0.6575, reason: 'Commodity weakness, dollar strength building', timeframe: 'H1', timestamp: '15:08 UTC' },
  { pair: 'USD/CAD', direction: 'buy', confidence: 61, entry: 1.3648, tp: 1.3720, sl: 1.3595, reason: 'Oil support fading, BOC dovish tilt', timeframe: 'H4', timestamp: '09:44 UTC' },
  { pair: 'NZD/USD', direction: 'sell', confidence: 69, entry: 0.5982, tp: 0.5920, sl: 0.6035, reason: 'RBNZ dovish pivot, technical breakdown', timeframe: 'D1', timestamp: '11:30 UTC' },
  { pair: 'EUR/GBP', direction: 'buy', confidence: 55, entry: 0.8551, tp: 0.8605, sl: 0.8510, reason: 'Cross-pair consolidation, ECB hawkish tone', timeframe: 'H1', timestamp: '13:20 UTC' },
]

export function useActiveSignals() {
  const signals = ref<ActiveSignal[]>(MOCK_SIGNALS)
  const pending = ref(false)
  const error = ref<Error | null>(null)

  return { signals, pending, error }
}
