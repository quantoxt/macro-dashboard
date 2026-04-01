import { readStorage, writeStorage } from '../../utils/storage'
import { INSTRUMENTS, fetchAllTimeframes } from '../../utils/yahoo'
import type { Timeframe } from '../../utils/yahoo'
import { scoreTimeframe, classifyBias, shouldWait } from '../../utils/calculations'

interface HeatmapInstrument {
  symbol: string
  timeframes: Record<string, number>
  totalScore: number
  bias: string
  wait: boolean
}

export default defineEventHandler(async () => {
  console.log('[Cron] Updating heatmap...')

  const instruments: HeatmapInstrument[] = []

  for (const inst of INSTRUMENTS) {
    try {
      const candles = await fetchAllTimeframes(inst.yahooSymbol)

      const timeframes: Record<string, number> = {}
      const tfKeys: Timeframe[] = ['1month', '1week', '1day', '4h', '1h']
      let totalScore = 0
      let highTfScore = 0
      let lowTfScore = 0

      for (const tf of tfKeys) {
        const tfCandles = candles[tf]
        if (!tfCandles || tfCandles.length < 20) {
          timeframes[tf] = 0
          continue
        }

        const score = scoreTimeframe(tfCandles)
        timeframes[tf] = score.total
        totalScore += score.total

        if (tf === '1month' || tf === '1week') {
          highTfScore += score.total
        }
        if (tf === '1h' || tf === '4h') {
          lowTfScore += score.total
        }
      }

      const wait = shouldWait(highTfScore, lowTfScore)
      const bias = classifyBias(totalScore, wait)

      instruments.push({
        symbol: inst.symbol,
        timeframes,
        totalScore,
        bias,
        wait,
      })

      // Small gap between instruments
      await new Promise(r => setTimeout(r, 1000))
    }
    catch (err) {
      console.error(`[Heatmap] Failed for ${inst.symbol}:`, err)
      instruments.push({
        symbol: inst.symbol,
        timeframes: { '1month': 0, '1week': 0, '1day': 0, '4h': 0, '1h': 0 },
        totalScore: 0,
        bias: 'Neutral',
        wait: false,
      })
    }
  }

  const payload = {
    instruments,
    updatedAt: new Date().toISOString(),
  }

  await writeStorage('heatmap-cache.json', payload)

  console.log(`[Cron] Heatmap updated: ${instruments.length} instruments scored`)

  return payload
})
