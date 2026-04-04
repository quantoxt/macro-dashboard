export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'
  const id = getRouterParam(event, 'id')!

  try {
    return await $fetch(`${engineUrl}/telegram/templates/${id}/reset`, {
      method: 'POST',
      timeout: 15000,
    })
  }
  catch (err: any) {
    console.error('[Telegram Templates] Reset failed:', err.message || err)
    throw createError({
      statusCode: err.response?.status || 500,
      message: err.data?.detail || 'Failed to reset template',
    })
  }
})
