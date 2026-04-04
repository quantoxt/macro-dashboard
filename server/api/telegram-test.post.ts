export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'
  const body = await readBody(event)

  try {
    return await $fetch(`${engineUrl}/telegram/test`, {
      method: 'POST',
      body: body || {},
      timeout: 15000,
    })
  }
  catch (err: any) {
    console.error('[Telegram Test] Failed:', err.message || err)
    throw createError({
      statusCode: err.response?.status || 500,
      message: err.data?.detail || 'Failed to send test message',
    })
  }
})
