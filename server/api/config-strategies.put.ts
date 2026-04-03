export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const engineUrl = (config.signalEngineUrl as string) || 'http://localhost:8081'

  const body = await readBody(event)
  if (!body || !body.strategyName) {
    throw createError({ statusCode: 400, statusMessage: 'Missing strategyName in body' })
  }

  const { strategyName, ...params } = body

  try {
    const data = await $fetch(`${engineUrl}/config/strategies/${strategyName}`, {
      method: 'PUT',
      body: params,
      timeout: 10000,
    })
    return data
  }
  catch (err: any) {
    console.error('[Config] Failed to update strategy:', err.message || err)
    throw createError({ statusCode: 502, statusMessage: 'Failed to update strategy' })
  }
})
