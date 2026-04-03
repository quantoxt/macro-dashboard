export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  const body = await readBody(event)
  if (!body) {
    throw createError({ statusCode: 400, statusMessage: 'Missing request body' })
  }

  try {
    const data = await $fetch(`${engineUrl}/backtest`, {
      method: 'POST',
      body,
      timeout: 120000,
    })
    return data
  }
  catch (err: any) {
    console.error('[Backtest] Failed:', err.message || err)
    throw createError({ statusCode: 502, statusMessage: 'Backtest failed' })
  }
})
