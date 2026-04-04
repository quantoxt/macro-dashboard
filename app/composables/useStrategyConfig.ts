export interface StrategyConfig {
  enabled: boolean
  minConfidence?: number
  minConfirmations?: number
  minRiskReward?: number
  atrSlMultiplier?: number
  atrTpMultiplier?: number
  rsiBuyThreshold?: number
  rsiSellThreshold?: number
}

export interface StrategyConfigs {
  strategies: Record<string, StrategyConfig>
  error?: string
}

export function useStrategyConfig() {
  const configs = ref<Record<string, StrategyConfig>>({})
  const pending = ref(true)
  const error = ref<string | null>(null)
  const saving = ref(false)
  const saveSuccess = ref<string | null>(null)

  async function fetchConfig() {
    try {
      const res = await $fetch<StrategyConfigs>('/api/config-strategies')
      configs.value = res.strategies ?? {}
      error.value = res.error ?? null
    }
    catch (err: any) {
      error.value = 'Signal engine unavailable'
    }
    finally {
      pending.value = false
    }
  }

  async function updateStrategy(name: string, params: Partial<StrategyConfig>) {
    saving.value = true
    saveSuccess.value = null
    error.value = null

    try {
      await $fetch('/api/config-strategies', {
        method: 'PUT',
        body: { strategyName: name, ...params },
      })
      saveSuccess.value = name
      // Re-fetch to get updated state
      await fetchConfig()
    }
    catch (err: any) {
      error.value = err.data?.statusMessage || 'Failed to save'
    }
    finally {
      saving.value = false
    }
  }

  onMounted(() => fetchConfig())

  return { configs, pending, error, saving, saveSuccess, updateStrategy, fetchConfig }
}
