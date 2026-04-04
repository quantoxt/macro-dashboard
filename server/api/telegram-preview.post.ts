export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'
  const body = await readBody(event)

  try {
    return await $fetch(`${engineUrl}/telegram/preview`, {
      method: 'POST',
      body,
      timeout: 15000,
    })
  }
  catch (err: any) {
    console.error('[Telegram Preview] Failed:', err.message || err)
    throw createError({
      statusCode: err.response?.status || 500,
      message: err.data?.detail || 'Failed to generate preview',
    })
  }
})
