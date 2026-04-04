export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const data = await $fetch(`${engineUrl}/tracker/performance`, { timeout: 15000 })
    return data
  }
  catch (err: any) {
    console.error('[Tracker] Failed to fetch performance:', err.message || err)
    return {
      strategies: {},
      overall: { total: 0, wins: 0, losses: 0, expired: 0, pending: 0, winRate: 0, totalPnlPips: 0, avgDurationHours: 0 },
      error: 'Signal engine unavailable',
    }
  }
})
