export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'
  const body = await readBody(event)

  try {
    return await $fetch(`${engineUrl}/telegram/settings`, {
      method: 'PUT',
      body,
      timeout: 15000,
    })
  }
  catch (err: any) {
    console.error('[Telegram Settings] PUT failed:', err.message || err)
    throw createError({
      statusCode: err.response?.status || 500,
      message: err.data?.detail || 'Failed to update settings',
    })
  }
})
