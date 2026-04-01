interface FredObservation {
  date: string
  value: string
}

interface FredResponse {
  observations: FredObservation[]
}

export interface YieldData {
  currency: string
  seriesId: string
  latest: number | null
  history: { date: string, value: number | null }[]
}

const SERIES: { currency: string, seriesId: string }[] = [
  { currency: 'USD', seriesId: 'DGS2' },
  { currency: 'EUR', seriesId: 'ECBMLFR' }, // ECB Main Refinancing Rate
  { currency: 'GBP', seriesId: 'IUDSOIA' },
  { currency: 'JPY', seriesId: 'INTDSRJPM193N' },
  { currency: 'AUD', seriesId: 'IRLTLT01AUM156N' },
  { currency: 'NZD', seriesId: 'IRSTCI01NZM156N' },
  { currency: 'CAD', seriesId: 'IRLTLT01CAM156N' },
  { currency: 'CHF', seriesId: 'IRLTLT01CHM156N' },
]

export async function fetchYields(apiKey: string): Promise<YieldData[]> {
  const results = await Promise.all(
    SERIES.map(async ({ currency, seriesId }) => {
      try {
        const url = `https://api.stlouisfed.org/fred/series/observations`
          + `?series_id=${seriesId}`
          + `&api_key=${apiKey}`
          + `&file_type=json`
          + `&limit=40`
          + `&sort_order=desc`

        const res = await $fetch<FredResponse>(url)

        const history = (res.observations ?? [])
          .filter(o => o.value !== '.')
          .map(o => ({
            date: o.date,
            value: Number.parseFloat(o.value),
          }))

        return {
          currency,
          seriesId,
          latest: history.length > 0 ? history[0]!.value : null,
          history,
        }
      }
      catch (err) {
        console.error(`[FRED] Failed to fetch ${seriesId} (${currency}):`, err)
        return { currency, seriesId, latest: null, history: [] }
      }
    }),
  )

  return results
}
