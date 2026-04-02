export interface MarketPulse {
  session: string
  sessionTime: string
  regime: 'risk-on' | 'risk-off' | 'neutral'
  regimeConfidence: number
  volatilityIndex: number
  volatilityLabel: string
  newsWarnings: number
  consolidationPairs: string[]
  nextEvent: string
  nextEventTime: string
}

const MOCK_PULSE: MarketPulse = {
  session: 'London / New York',
  sessionTime: '14:00–17:00 UTC',
  regime: 'risk-on',
  regimeConfidence: 72,
  volatilityIndex: 18.4,
  volatilityLabel: 'Moderate',
  newsWarnings: 2,
  consolidationPairs: ['USD/CHF', 'EUR/GBP'],
  nextEvent: 'US ISM Manufacturing PMI',
  nextEventTime: '15:00 UTC',
}

export function useMarketPulse() {
  const pulse = ref<MarketPulse>(MOCK_PULSE)
  const pending = ref(false)
  const error = ref<Error | null>(null)

  return { pulse, pending, error }
}
