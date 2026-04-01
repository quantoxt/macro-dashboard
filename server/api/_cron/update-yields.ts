import { readStorage, writeStorage } from '../../utils/storage'
import { fetchYields } from '../../utils/fred'
import { calculateAllSpreads } from '../../utils/calculations'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiKey = config.fredApiKey as string

  if (!apiKey) {
    throw createError({ statusCode: 500, statusMessage: 'FRED_API_KEY not configured' })
  }

  console.log('[Cron] Updating yield spreads...')

  const yields = await fetchYields(apiKey)

  // Build history matrix: each row is { USD: val, EUR: val, ... } for a date
  const dateSet = new Set<string>()
  for (const y of yields) {
    for (const h of y.history) {
      dateSet.add(h.date)
    }
  }
  const dates = [...dateSet].sort().reverse()

  const spreadHistory = dates.map((date) => {
    const row: Record<string, number | null> = {}
    for (const y of yields) {
      const entry = y.history.find(h => h.date === date)
      row[y.currency] = entry?.value ?? null
    }
    return row
  })

  const { buyCandidates, sellCandidates } = calculateAllSpreads(yields, spreadHistory)

  const payload = {
    yields,
    spreadHistory,
    buyCandidates,
    sellCandidates,
    updatedAt: new Date().toISOString(),
  }

  await writeStorage('yields.json', payload)

  console.log(`[Cron] Yield spreads updated: ${buyCandidates.length} buy, ${sellCandidates.length} sell`)

  return payload
})
