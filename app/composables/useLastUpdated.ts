export function useLastUpdatedStore() {
  return useState<{ yield?: string; heatmap?: string }>('last-updated', () => ({}))
}

export function useLastUpdated() {
  const store = useLastUpdatedStore()

  const pending = computed(() => {
    const s = store.value
    return !s.yield && !s.heatmap
  })

  const formatted = computed(() => {
    const dates = [store.value.yield, store.value.heatmap]
      .filter(Boolean)
      .sort()
    if (dates.length === 0) return ''
    const d = new Date(dates.at(-1)!)
    const hh = String(d.getUTCHours()).padStart(2, '0')
    const mm = String(d.getUTCMinutes()).padStart(2, '0')
    const ss = String(d.getUTCSeconds()).padStart(2, '0')
    return `${hh}:${mm}:${ss} UTC`
  })

  return { formatted, pending }
}
