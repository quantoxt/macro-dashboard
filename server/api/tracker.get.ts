export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const data = await $fetch(`${engineUrl}/tracker/signals`, { timeout: 15000 })
    return {
      signals: data.signals ?? [],
      stats: data.stats ?? { total: 0, wins: 0, losses: 0, expired: 0, pending: 0, winRate: 0, totalPnlPips: 0 },
    }
  }
  catch (err: any) {
    console.error('[Tracker] Failed to fetch signals:', err.message || err)
    return {
      signals: [],
      stats: { total: 0, wins: 0, losses: 0, expired: 0, pending: 0, winRate: 0, totalPnlPips: 0 },
      error: 'Signal engine unavailable',
    }
  }
})
