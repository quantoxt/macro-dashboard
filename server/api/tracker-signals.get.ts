export default defineEventHandler(async () => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const data = await $fetch(`${engineUrl}/tracker/signals`, { timeout: 15000 })
    return data
  }
  catch (err: any) {
    console.error('[Tracker Signals] Failed to fetch:', err.message || err)
    return {
      signals: [],
      stats: { total: 0, pending: 0, wins: 0, losses: 0, expired: 0, winRate: 0, avgPnlPips: 0 },
      error: 'Signal engine unavailable',
    }
  }
})
