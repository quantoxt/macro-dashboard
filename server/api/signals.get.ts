export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const data = await $fetch<{ signals: any[], updatedAt: string }>(`${engineUrl}/signals`, {
      timeout: 30000,
    })
    return {
      signals: data.signals ?? [],
      updatedAt: data.updatedAt ?? null,
    }
  }
  catch (err: any) {
    console.error('[Signals] Failed to fetch from engine:', err.message || err)
    return {
      signals: [],
      updatedAt: null,
      error: 'Signal engine unavailable',
    }
  }
})
