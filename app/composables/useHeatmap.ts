export interface HeatmapRow {
  instrument: string
  scores: Record<string, number>
  total: number
  bias: string
  wait?: boolean
}

export const TIMEFRAMES = ['Monthly', 'Weekly', 'Daily', 'H4', 'H1'] as const

const TF_KEY_MAP: Record<string, string> = {
  '1month': 'Monthly',
  '1week': 'Weekly',
  '1day': 'Daily',
  '4h': 'H4',
  '1h': 'H1',
}

export function useHeatmap() {
  const store = useLastUpdatedStore()
  const { data, pending, error } = useFetch<{
    updatedAt: string
    instruments: {
      symbol: string
      timeframes: Record<string, number>
      totalScore: number
      bias: string
      wait?: boolean
    }[]
  }>('/api/heatmap', {
    refetchInterval: 900000,
  })

  const instruments = computed<HeatmapRow[]>(() =>
    data.value?.instruments.map(inst => {
      const scores: Record<string, number> = {}
      for (const [key, value] of Object.entries(inst.timeframes)) {
        const mapped = TF_KEY_MAP[key]
        if (mapped) scores[mapped] = value
      }
      return {
        instrument: inst.symbol,
        scores,
        total: inst.totalScore,
        bias: inst.bias,
        wait: inst.wait,
      }
    }) ?? [],
  )

  const updatedAt = computed(() => data.value?.updatedAt ?? null)

  watch(updatedAt, (v) => {
    if (v) store.value.heatmap = v
  }, { immediate: true })

  return { instruments, timeframes: TIMEFRAMES, updatedAt, pending, error }
}
