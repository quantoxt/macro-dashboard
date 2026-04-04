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

export function useMarketPulse() {
  const pulse = ref<MarketPulse | null>(null)
  const pending = ref(true)
  const error = ref<string | null>(null)
  let intervalId: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    try {
      const res: MarketPulse & { error?: string } = await $fetch('/api/market-pulse')

      if (!res || res.error) {
        error.value = res?.error || 'Failed to load market pulse'
        pulse.value = null
      }
      else {
        pulse.value = res
        error.value = null
      }
    }
    catch (err: any) {
      error.value = 'Signal engine unavailable'
      pulse.value = null
    }
    finally {
      pending.value = false
    }
  }

  onMounted(() => {
    refresh()
    intervalId = setInterval(refresh, 2.5 * 60 * 1000)
  })

  onScopeDispose(() => {
    if (intervalId) clearInterval(intervalId)
  })

  return { pulse, pending, error, refresh }
}
