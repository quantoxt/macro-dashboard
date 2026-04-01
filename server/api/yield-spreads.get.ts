import { getYieldData } from '../utils/yield-service'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiKey = config.fredApiKey as string

  if (!apiKey) {
    throw createError({ statusCode: 500, statusMessage: 'FRED_API_KEY not configured' })
  }

  try {
    const data = await getYieldData(apiKey)
    return {
      updatedAt: data.updatedAt,
      buyCandidates: data.buyCandidates ?? [],
      sellCandidates: data.sellCandidates ?? [],
    }
  }
  catch (err) {
    console.error('[Yield Spreads] Failed to fetch:', err)
    return {
      updatedAt: null,
      buyCandidates: [],
      sellCandidates: [],
    }
  }
})
