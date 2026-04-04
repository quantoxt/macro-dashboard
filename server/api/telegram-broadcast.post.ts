export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  try {
    const body = await readBody(event)
    return await $fetch(`${engineUrl}/telegram/broadcast`, {
      method: 'POST',
      body,
      timeout: 30000, // broadcast may take longer
    })
  }
  catch (err: any) {
    console.error('[Telegram Broadcast] POST failed:', err.message || err)
    return { error: 'Signal engine unavailable' }
  }
})
