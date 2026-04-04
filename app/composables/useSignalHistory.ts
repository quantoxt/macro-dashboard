interface TrackerStats {
  total: number
  pending: number
  wins: number
  losses: number
  expired: number
  expiredTime: number
  expiredAdverse: number
  winRate: number
  avgPnlPips: number
}

interface TrackerSignalsResponse {
  signals: TrackedSignal[]
  stats: TrackerStats
  error?: string
}

export function useSignalHistory() {
  const signals = ref<TrackedSignal[]>([])
  const stats = ref<TrackerStats>({ total: 0, pending: 0, wins: 0, losses: 0, expired: 0, expiredTime: 0, expiredAdverse: 0, winRate: 0, avgPnlPips: 0 })
  const pending = ref(true)
  const error = ref<string | null>(null)

  // Filters
  const instrumentFilter = ref('all')
  const strategyFilter = ref('all')
  const outcomeFilter = ref('all')

  const filteredSignals = computed(() => {
    let result = signals.value

    if (instrumentFilter.value !== 'all') {
      result = result.filter(s => s.instrument === instrumentFilter.value)
    }
    if (strategyFilter.value !== 'all') {
      result = result.filter(s => s.strategy === strategyFilter.value)
    }
    if (outcomeFilter.value !== 'all') {
      result = result.filter(s => {
        if (outcomeFilter.value.startsWith('EXPIRED') && s.outcome === 'EXPIRED') return true
        return s.outcome === outcomeFilter.value
      })
    }

    // Sort by generatedAt descending
    return [...result].sort((a, b) => new Date(b.generatedAt).getTime() - new Date(a.generatedAt).getTime())
  })

  let intervalId: ReturnType<typeof setInterval> | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  async function fetchSignals() {
    try {
      const res: TrackerSignalsResponse = await $fetch('/api/tracker-signals')

      if (!res || res.error) {
        error.value = res?.error || 'Failed to load signals'
        signals.value = []
      }
      else {
        signals.value = res.signals ?? []
        stats.value = res.stats ?? { total: 0, pending: 0, wins: 0, losses: 0, expired: 0, expiredTime: 0, expiredAdverse: 0, winRate: 0, avgPnlPips: 0 }
        error.value = null
      }
    }
    catch (err: any) {
      error.value = 'Signal engine unavailable'
      signals.value = []
    }
    finally {
      pending.value = false
    }
  }

  async function updateSignal(id: string, data: Partial<Pick<TrackedSignal, 'userStatus' | 'notes' | 'manualEntry' | 'manualExit'>>) {
    // Optimistic update
    const idx = signals.value.findIndex(s => s.id === id)
    if (idx === -1) return

    const original = { ...signals.value[idx] }

    // Apply locally
    if (data.userStatus !== undefined) signals.value[idx].userStatus = data.userStatus
    if (data.notes !== undefined) signals.value[idx].notes = data.notes
    if (data.manualEntry !== undefined) signals.value[idx].manualEntry = data.manualEntry
    if (data.manualExit !== undefined) signals.value[idx].manualExit = data.manualExit

    try {
      const res = await $fetch<{ signal: TrackedSignal }>(`/api/tracker-signals/${id}`, {
        method: 'PUT',
        body: {
          user_status: data.userStatus,
          notes: data.notes,
          manual_entry: data.manualEntry,
          manual_exit: data.manualExit,
        },
      })

      // Replace with server response
      if (res?.signal) {
        signals.value[idx] = res.signal
      }
    }
    catch (err: any) {
      // Revert on failure
      signals.value[idx] = original
      console.error('[SignalHistory] Update failed:', err.message || err)
    }
  }

  function debouncedSaveNotes(id: string, notes: string) {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      updateSignal(id, { notes })
    }, 1000)
  }

  function relativeTime(iso: string): string {
    const now = Date.now()
    const then = new Date(iso).getTime()
    const diff = now - then

    const mins = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 30) return `${days}d ago`
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  onMounted(() => {
    fetchSignals()
    intervalId = setInterval(fetchSignals, 60000)
  })

  onScopeDispose(() => {
    if (intervalId) clearInterval(intervalId)
    if (debounceTimer) clearTimeout(debounceTimer)
  })

  return {
    signals,
    stats,
    filteredSignals,
    pending,
    error,
    instrumentFilter,
    strategyFilter,
    outcomeFilter,
    fetchSignals,
    updateSignal,
    debouncedSaveNotes,
    relativeTime,
  }
}
