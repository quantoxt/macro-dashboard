export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const data = await $fetch(`${engineUrl}/config/strategies`, { timeout: 10000 })
    return data
  }
  catch (err: any) {
    console.error('[Config] Failed to fetch strategies:', err.message || err)
    return {
      strategies: {},
      error: 'Signal engine unavailable',
    }
  }
})
