export interface StrategyPerformance {
  winRate: number
  totalTrades: number
  avgPips: number
  profitFactor: number
  maxDrawdown: number
  confidenceTrend: 'rising' | 'stable' | 'declining'
  weeklyPnl: number
  streak: number
  streakType: 'wins' | 'losses'
  recentResults: ('W' | 'L')[]
}

const MOCK_PERFORMANCE: StrategyPerformance = {
  winRate: 64.2,
  totalTrades: 156,
  avgPips: 23.8,
  profitFactor: 1.87,
  maxDrawdown: -4.2,
  confidenceTrend: 'rising',
  weeklyPnl: 187,
  streak: 4,
  streakType: 'wins',
  recentResults: ['W', 'W', 'L', 'W', 'W', 'L', 'W', 'W', 'W', 'L'],
}

export function useStrategyPerformance() {
  const performance = ref<StrategyPerformance>(MOCK_PERFORMANCE)
  const pending = ref(false)
  const error = ref<Error | null>(null)

  return { performance, pending, error }
}
