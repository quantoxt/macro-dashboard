import type { OhlcCandle } from './yahoo'

// --- Yield Spread Calculations ---

export interface SpreadEntry {
  pair: string
  baseCurrency: string
  quoteCurrency: string
  spread: number
  ma20: number | null
  weeklyDelta: number | null
  ma20Signal: 'above' | 'below' | 'neutral' | null
}

interface YieldRecord {
  currency: string
  latest: number | null
  history: { date: string, value: number | null }[]
}

const CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CAD', 'CHF'] as const

export function generatePairs(): [string, string][] {
  const pairs: [string, string][] = []
  for (let i = 0; i < CURRENCIES.length; i++) {
    for (let j = i + 1; j < CURRENCIES.length; j++) {
      pairs.push([CURRENCIES[i]!, CURRENCIES[j]!])
    }
  }
  return pairs
}

export function calculateAllSpreads(
  yields: YieldRecord[],
  yieldHistory: Array<Record<string, number | null>>,
): { buyCandidates: SpreadEntry[], sellCandidates: SpreadEntry[] } {
  const yieldMap = new Map(yields.map(y => [y.currency, y]))
  const pairs = generatePairs()

  const allSpreads: SpreadEntry[] = []

  for (const [base, quote] of pairs) {
    const baseYield = yieldMap.get(base)
    const quoteYield = yieldMap.get(quote)

    if (!baseYield?.latest || !quoteYield?.latest) continue

    // Both directions
    for (const [b, q] of [[base, quote], [quote, base]] as [string, string][]) {
      const bYield = yieldMap.get(b)!
      const qYield = yieldMap.get(q)!
      const spread = bYield.latest! - qYield.latest!

      // Calculate MA20 and weekly delta from history
      const spreadHistory = yieldHistory.map((record) => {
        const bv = record[b] ?? null
        const qv = record[q] ?? null
        if (bv === null || qv === null) return null
        return bv - qv
      }).filter((v): v is number => v !== null)

      const ma20 = spreadHistory.length >= 20
        ? Number((spreadHistory.slice(0, 20).reduce((a, b) => a + b, 0) / 20).toFixed(4))
        : null

      const weeklyDelta = spreadHistory.length >= 5
        ? Number((spread - spreadHistory[4]!).toFixed(4))
        : null

      let ma20Signal: SpreadEntry['ma20Signal'] = null
      if (ma20 !== null) {
        ma20Signal = spread > ma20 ? 'above' : spread < ma20 ? 'below' : 'neutral'
      }

      allSpreads.push({
        pair: `${b}${q}`,
        baseCurrency: b,
        quoteCurrency: q,
        spread: Number(spread.toFixed(4)),
        ma20,
        weeklyDelta,
        ma20Signal,
      })
    }
  }

  // Sort by spread descending
  allSpreads.sort((a, b) => b.spread - a.spread)

  const buyCandidates = allSpreads.filter(s => s.spread > 0).slice(0, 7).map((s, i) => ({
    ...s,
    rank: i + 1,
  }))

  const sellCandidates = allSpreads.filter(s => s.spread < 0).slice(-7).reverse().map((s, i) => ({
    ...s,
    rank: i + 1,
  }))

  return { buyCandidates, sellCandidates }
}

// --- RSI Calculation ---

export function calculateRSI(candles: OhlcCandle[], period = 14): number {
  if (candles.length < period + 1) return 50

  const closes = candles.map(c => c.close)
  let gains = 0
  let losses = 0

  for (let i = 1; i <= period; i++) {
    const change = closes[i]! - closes[i - 1]!
    if (change > 0) gains += change
    else losses += Math.abs(change)
  }

  let avgGain = gains / period
  let avgLoss = losses / period

  for (let i = period + 1; i < closes.length; i++) {
    const change = closes[i]! - closes[i - 1]!
    avgGain = (avgGain * (period - 1) + Math.max(change, 0)) / period
    avgLoss = (avgLoss * (period - 1) + Math.abs(Math.min(change, 0))) / period
  }

  if (avgLoss === 0) return 100
  const rs = avgGain / avgLoss
  return Number((100 - 100 / (1 + rs)).toFixed(2))
}

// --- SMA Calculation ---

export function calculateSMA(candles: OhlcCandle[], period: number): number | null {
  if (candles.length < period) return null
  const sum = candles.slice(-period).reduce((acc, c) => acc + c.close, 0)
  return Number((sum / period).toFixed(6))
}

// --- Heatmap Scoring ---

export interface TimeframeScore {
  trend: number
  momentum: number
  structure: number
  total: number
}

export function scoreTimeframe(candles: OhlcCandle[]): TimeframeScore {
  if (candles.length < 20) {
    return { trend: 0, momentum: 0, structure: 0, total: 0 }
  }

  // Trend: price vs SMA20
  const sma20 = calculateSMA(candles, 20)
  const currentPrice = candles[candles.length - 1]!.close
  const trend = sma20 !== null
    ? currentPrice > sma20 ? 1 : currentPrice < sma20 ? -1 : 0
    : 0

  // Momentum: RSI(14)
  const rsi = calculateRSI(candles, 14)
  const momentum = rsi > 55 ? 1 : rsi < 45 ? -1 : 0

  // Structure: last 3 candles making higher highs/lows or lower
  const last3 = candles.slice(-3)
  const higherStructure = last3[2]!.high > last3[1]!.high && last3[1]!.high > last3[0]!.high
    && last3[2]!.low > last3[1]!.low
  const lowerStructure = last3[2]!.high < last3[1]!.high && last3[1]!.high < last3[0]!.high
    && last3[2]!.low < last3[1]!.low

  const structure = higherStructure ? 1 : lowerStructure ? -1 : 0

  return {
    trend,
    momentum,
    structure,
    total: trend + momentum + structure,
  }
}

export type Bias = 'Very Bullish' | 'Bullish' | 'Neutral' | 'Bearish' | 'Very Bearish' | 'WAIT'

export function classifyBias(totalScore: number, wait: boolean): Bias {
  if (wait) return 'WAIT'
  if (totalScore >= 8) return 'Very Bullish'
  if (totalScore >= 4) return 'Bullish'
  if (totalScore <= -8) return 'Very Bearish'
  if (totalScore <= -4) return 'Bearish'
  return 'Neutral'
}

export function shouldWait(
  highTfScore: number,
  lowTfScore: number,
): boolean {
  // WAIT if high timeframes strongly disagree with low timeframes
  return (highTfScore >= 3 && lowTfScore <= -2)
    || (highTfScore <= -3 && lowTfScore >= 2)
}
