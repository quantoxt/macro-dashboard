export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const data = await $fetch(`${engineUrl}/market-pulse`, {
      timeout: 15000,
    })
    return data
  }
  catch (err: any) {
    console.error('[Market Pulse] Failed to fetch from engine:', err.message || err)
    return {
      session: '--',
      sessionTime: '--',
      regime: 'neutral',
      regimeConfidence: 0,
      volatilityIndex: 0,
      volatilityLabel: '--',
      newsWarnings: 0,
      consolidationPairs: [],
      nextEvent: '--',
      nextEventTime: '--',
      error: 'Signal engine unavailable',
    }
  }
})
