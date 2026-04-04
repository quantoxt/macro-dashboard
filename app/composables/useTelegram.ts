export interface TelegramSettings {
  parse_mode: 'markdown' | 'plain'
  batch_window: number
  outcome_alerts: boolean
  outcome_win: boolean
  outcome_loss: boolean
  outcome_expired: boolean
  quiet_hours_enabled: boolean
  quiet_hours_start: string
  quiet_hours_end: string
  quiet_hours_timezone: string
  cooldown_enabled: boolean
  cooldown_hours: number
  daily_summary_enabled: boolean
  daily_summary_time: string
  tradingview_links: boolean
  instrument_notifications: Record<string, boolean>
  strategy_notifications: Record<string, boolean>
  min_confidence: number
  chats: Array<{ id: string; label: string; enabled: boolean }>
}

export interface TemplateData {
  id: string
  name: string
  template: string
  description: string
}

export function useTelegram() {
  const settings = ref<TelegramSettings | null>(null)
  const templates = ref<Record<string, TemplateData>>({})
  const loading = ref(true)
  const error = ref<string | null>(null)

  // Debounced settings save
  let settingsTimer: ReturnType<typeof setTimeout> | null = null
  const dirtySettings = ref<Partial<TelegramSettings> | null>(null)

  async function fetchSettings() {
    try {
      const res = await $fetch<TelegramSettings>('/api/telegram-settings')
      if (res && !('error' in res)) {
        settings.value = res
        error.value = null
      }
      else {
        error.value = (res as any).error || 'Failed to load settings'
      }
    }
    catch {
      error.value = 'Signal engine unavailable'
    }
  }

  async function fetchTemplates() {
    try {
      const res = await $fetch<{ templates: Record<string, TemplateData> }>('/api/telegram-templates')
      templates.value = res?.templates ?? {}
    }
    catch {
      // Templates are non-critical
    }
  }

  async function updateSettings(partial: Partial<TelegramSettings>) {
    // Optimistic local update
    if (settings.value) {
      settings.value = { ...settings.value, ...partial }
    }

    // Merge into dirty batch
    dirtySettings.value = { ...dirtySettings.value, ...partial }

    // Debounce the actual API call
    if (settingsTimer) clearTimeout(settingsTimer)
    settingsTimer = setTimeout(async () => {
      const changes = dirtySettings.value
      dirtySettings.value = null
      if (!changes) return

      try {
        await $fetch('/api/telegram-settings', {
          method: 'PUT',
          body: changes,
        })
      }
      catch (err: any) {
        error.value = 'Failed to save settings'
        // Re-fetch to get server state
        await fetchSettings()
      }
    }, 2000)
  }

  async function updateTemplate(id: string, template: string) {
    try {
      const res = await $fetch<{ template: TemplateData }>(`/api/telegram-templates/${id}`, {
        method: 'PUT',
        body: { template },
      })
      if (res?.template) {
        templates.value[id] = res.template
      }
    }
    catch (err: any) {
      error.value = 'Failed to save template'
    }
  }

  async function resetTemplate(id: string) {
    try {
      const res = await $fetch<{ template: TemplateData }>(`/api/telegram-templates/${id}/reset`, {
        method: 'POST',
      })
      if (res?.template) {
        templates.value[id] = res.template
      }
    }
    catch (err: any) {
      error.value = 'Failed to reset template'
    }
  }

  async function preview(templateId: string, variables: Record<string, string>): Promise<string> {
    try {
      const res = await $fetch<{ rendered: string }>('/api/telegram-preview', {
        method: 'POST',
        body: { template_id: templateId, variables },
      })
      return res?.rendered ?? ''
    }
    catch {
      return 'Preview unavailable'
    }
  }

  async function sendTest(templateId: string = 'test', variables: Record<string, string> = {}): Promise<{ sent: boolean; message: string }> {
    try {
      const res = await $fetch<{ sent: boolean; message: string }>('/api/telegram-test', {
        method: 'POST',
        body: { template_id: templateId, variables },
      })
      return res
    }
    catch (err: any) {
      return { sent: false, message: err.data?.message || 'Failed to send test' }
    }
  }

  onMounted(async () => {
    await Promise.all([fetchSettings(), fetchTemplates()])
    loading.value = false
  })

  onScopeDispose(() => {
    if (settingsTimer) clearTimeout(settingsTimer)
  })

  return {
    settings,
    templates,
    loading,
    error,
    fetchSettings,
    fetchTemplates,
    updateSettings,
    updateTemplate,
    resetTemplate,
    preview,
    sendTest,
  }
}
