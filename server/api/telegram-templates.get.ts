export default defineEventHandler(async () => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    return await $fetch(`${engineUrl}/telegram/templates`, { timeout: 15000 })
  }
  catch (err: any) {
    console.error('[Telegram Templates] GET failed:', err.message || err)
    return { templates: {}, error: 'Signal engine unavailable' }
  }
})
