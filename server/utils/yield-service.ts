import { fetchYields } from './fred'
import { calculateAllSpreads } from './calculations'

// In-memory cache
let cache: {
  buyCandidates: any[]
  sellCandidates: any[]
  updatedAt: string | null
} | null = null

let lastFetch = 0
const CACHE_TTL = 30 * 60 * 1000 // 30 minutes

export async function getYieldData(apiKey: string) {
  const now = Date.now()

  // Return cached data if still fresh
  if (cache && cache.updatedAt && (now - lastFetch) < CACHE_TTL) {
    return cache
  }

  // Fetch fresh data
  const yields = await fetchYields(apiKey)

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

  cache = {
    buyCandidates,
    sellCandidates,
    updatedAt: new Date().toISOString(),
  }
  lastFetch = now

  console.log(`[Yields] Data refreshed: ${buyCandidates.length} buy, ${sellCandidates.length} sell`)
  return cache
}
