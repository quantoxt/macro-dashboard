export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const body = await readBody(event)
    return await $fetch(`${engineUrl}/telegram/subscribers`, {
      method: 'DELETE',
      body,
      timeout: 15000,
    })
  }
  catch (err: any) {
    console.error('[Telegram Subscribers] DELETE failed:', err.message || err)
    return { error: 'Signal engine unavailable' }
  }
})
