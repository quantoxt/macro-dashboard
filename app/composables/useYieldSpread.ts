export interface YieldPair {
  rank: number
  pair: string
  spread: number
  weeklyDelta: number
  ma20Above: boolean | null
}

export function useYieldSpread() {
  const store = useLastUpdatedStore()
  const { data, pending, error } = useFetch<{
    updatedAt: string
    buyCandidates: {
      rank: number
      pair: string
      spread: number
      weeklyDelta: number | null
      ma20: number | null
      ma20Signal: string | null
    }[]
    sellCandidates: {
      rank: number
      pair: string
      spread: number
      weeklyDelta: number | null
      ma20: number | null
      ma20Signal: string | null
    }[]
  }>('/api/yield-spreads', {
    refetchInterval: 1800000,
  })

  const buyCandidates = computed<YieldPair[]>(() =>
    data.value?.buyCandidates.map(c => ({
      rank: c.rank,
      pair: c.pair,
      spread: c.spread,
      weeklyDelta: c.weeklyDelta ?? 0,
      ma20Above: c.ma20Signal === 'above' ? true : c.ma20Signal === 'below' ? false : null,
    })) ?? [],
  )

  const sellCandidates = computed<YieldPair[]>(() =>
    data.value?.sellCandidates.map(c => ({
      rank: c.rank,
      pair: c.pair,
      spread: c.spread,
      weeklyDelta: c.weeklyDelta ?? 0,
      ma20Above: c.ma20Signal === 'above' ? true : c.ma20Signal === 'below' ? false : null,
    })) ?? [],
  )

  const maxSpread = computed(() =>
    Math.max(
      ...buyCandidates.value.map(c => c.spread),
      ...sellCandidates.value.map(c => Math.abs(c.spread)),
      1,
    ),
  )

  const updatedAt = computed(() => data.value?.updatedAt ?? null)

  watch(updatedAt, (v) => {
    if (v) store.value.yield = v
  }, { immediate: true })

  return { buyCandidates, sellCandidates, maxSpread, updatedAt, pending, error }
}
