import YahooFinance from 'yahoo-finance2'
const yahooFinance = new YahooFinance()

// --- Shared types (kept identical to twelvedata for drop-in compat) ---

export interface OhlcCandle {
  datetime: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type Timeframe = '1h' | '4h' | '1day' | '1week' | '1month'

export const INSTRUMENTS: { symbol: string, yahooSymbol: string }[] = [
  { symbol: 'XAUUSD', yahooSymbol: 'GC=F' },
  { symbol: 'XAGUSD', yahooSymbol: 'SI=F' },
  { symbol: 'USDJPY', yahooSymbol: 'USDJPY=X' },
  { symbol: 'GBPJPY', yahooSymbol: 'GBPJPY=X' },
  { symbol: 'BTCUSD', yahooSymbol: 'BTC-USD' },
]

// Yahoo interval + lookback duration per timeframe
const TF_CONFIG: Record<Timeframe, { interval: string, lookbackDays: number }> = {
  '1month': { interval: '1mo', lookbackDays: 365 * 5 },   // ~60 monthly candles
  '1week': { interval: '1wk', lookbackDays: 365 * 2 },    // ~104 weekly candles
  '1day': { interval: '1d', lookbackDays: 200 },           // ~130 daily candles
  '4h': { interval: '1h', lookbackDays: 100 },             // aggregate 1h→4h, ~600 4h candles
  '1h': { interval: '1h', lookbackDays: 40 },              // ~960 hourly candles
}

function yahooQuoteToCandle(q: {
  date: Date | number
  open: number
  high: number
  low: number
  close: number
  volume: number
}): OhlcCandle {
  const d = q.date instanceof Date ? q.date : new Date(q.date * 1000)
  return {
    datetime: d.toISOString(),
    open: q.open,
    high: q.high,
    low: q.low,
    close: q.close,
    volume: q.volume ?? 0,
  }
}

function aggregateTo4h(candles: OhlcCandle[]): OhlcCandle[] {
  if (candles.length === 0) return []

  const result: OhlcCandle[] = []

  for (let i = 0; i < candles.length; i += 4) {
    const chunk = candles.slice(i, i + 4)
    if (chunk.length < 2) break

    result.push({
      datetime: chunk[0]!.datetime,
      open: chunk[0]!.open,
      high: Math.max(...chunk.map(c => c.high)),
      low: Math.min(...chunk.map(c => c.low)),
      close: chunk[chunk.length - 1]!.close,
      volume: chunk.reduce((sum, c) => sum + c.volume, 0),
    })
  }

  return result
}

export async function fetchTimeSeries(
  symbol: string,
  interval: string,
  lookbackDays: number,
): Promise<OhlcCandle[]> {
  const period1 = new Date()
  period1.setDate(period1.getDate() - lookbackDays)

  try {
    const result = await yahooFinance.chart(symbol, {
      period1,
      interval: interval as any,
    })

    if (!result?.quotes || result.quotes.length === 0) {
      return []
    }

    return result.quotes
      .filter((q: any) => q.open != null && q.close != null)
      .map(yahooQuoteToCandle)
  }
  catch (err) {
    console.error(`[Yahoo] Failed ${symbol} ${interval}:`, (err as Error).message)
    return []
  }
}

export async function fetchAllTimeframes(
  yahooSymbol: string,
): Promise<Record<Timeframe, OhlcCandle[]>> {
  const results: [Timeframe, OhlcCandle[]][] = []

  for (const [tf, config] of Object.entries(TF_CONFIG) as [Timeframe, typeof TF_CONFIG[Timeframe]][]) {
    let candles = await fetchTimeSeries(yahooSymbol, config.interval, config.lookbackDays)

    // Aggregate 1h → 4h
    if (tf === '4h') {
      candles = aggregateTo4h(candles)
    }

    results.push([tf, candles])

    // Small delay to be respectful
    await new Promise(r => setTimeout(r, 300))
  }

  return Object.fromEntries(results) as Record<Timeframe, OhlcCandle[]>
}
