export default defineEventHandler(async () => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    return await $fetch(`${engineUrl}/telegram/subscribers`, { timeout: 15000 })
  }
  catch (err: any) {
    console.error('[Telegram Subscribers] GET failed:', err.message || err)
    return { error: 'Signal engine unavailable', subscribers: [], active_count: 0, total_count: 0 }
  }
})
