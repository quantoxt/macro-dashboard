<script setup lang="ts">
import { useTelegram } from '~/composables/useTelegram'
import type { TemplateData } from '~/composables/useTelegram'

const { templates, updateTemplate, resetTemplate, preview, sendTest, settings } = useTelegram()

const selectedId = ref<string>('signal_single')
const previewText = ref('')
const sending = ref(false)
const testResult = ref<{ sent: boolean; message: string } | null>(null)
const confirmingReset = ref(false)

// Local draft for template editing
const draft = ref('')
let draftTimer: ReturnType<typeof setTimeout> | null = null

// Sync draft when selection changes
watch(selectedId, () => {
  const t = templates.value[selectedId.value]
  draft.value = t?.template ?? ''
  previewText.value = ''
  confirmingReset.value = false
}, { immediate: true })

// Also sync when templates load
watch(() => templates.value[selectedId.value]?.template, (val) => {
  if (val !== undefined && !draftTimer) {
    draft.value = val
  }
})

// Debounced save on edit
function onEdit(val: string) {
  draft.value = val
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(() => {
    updateTemplate(selectedId.value, val)
    draftTimer = null
  }, 2000)
}

// Variable chips
const variables = [
  'instrument', 'direction', 'direction_emoji', 'strategy', 'confidence',
  'entry', 'sl', 'tp', 'rr', 'reasons', 'outcome', 'pnl_pips', 'pnl_sign',
  'notes', 'user_status', 'vix', 'vix_regime', 'session', 'signal_count',
  'tradingview_url', 'dashboard_url', 'timestamp',
]

function insertVariable(varName: string) {
  const textarea = document.querySelector<HTMLTextAreaElement>('[data-template-editor]')
  if (!textarea) return
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const insertion = `{${varName}}`
  const newVal = draft.value.slice(0, start) + insertion + draft.value.slice(end)
  draft.value = newVal
  onEdit(newVal)
  // Restore cursor position after Vue update
  nextTick(() => {
    textarea.selectionStart = textarea.selectionEnd = start + insertion.length
    textarea.focus()
  })
}

// Preview
async function generatePreview() {
  const sampleVars: Record<string, string> = {
    instrument: 'XAUUSD',
    direction: 'BUY',
    direction_emoji: '🟢',
    strategy: 'confluence_breakout',
    confidence: '75',
    entry: '2345.20',
    sl: '2340.00',
    tp: '2360.00',
    rr: '2.0',
    reasons: 'H4 uptrend, RSI at 55, Zone: buy',
    outcome: 'WIN',
    pnl_pips: '+45.0',
    pnl_sign: '+',
    notes: 'Good entry',
    user_status: 'taken',
    vix: '23.9',
    vix_regime: 'normal',
    session: 'EUROPEAN',
    signal_count: '3',
    tradingview_url: '📈 View Chart',
    dashboard_url: 'http://localhost:8080',
    timestamp: '2026-04-04 08:00',
  }
  previewText.value = await preview(selectedId.value, sampleVars)
}

// Test send
async function handleTest() {
  sending.value = true
  testResult.value = null
  testResult.value = await sendTest(selectedId.value)
  sending.value = false
}

// Reset
async function handleReset() {
  if (!confirmingReset.value) {
    confirmingReset.value = true
    return
  }
  await resetTemplate(selectedId.value)
  draft.value = templates.value[selectedId.value]?.template ?? ''
  confirmingReset.value = false
}

const templateList = computed(() =>
  Object.values(templates.value).sort((a, b) => a.name.localeCompare(b.name)),
)

const templateIcons: Record<string, string> = {
  signal_single: '📋',
  signal_batch: '📋',
  outcome_win: '✅',
  outcome_loss: '❌',
  outcome_expired: '⏰',
  daily_summary: '📊',
  brief: '📋',
  test: '🧪',
}

function varChip(name: string): string {
  return '{' + name + '}'
}
</script>

<template>
  <div v-if="!Object.keys(templates).length" class="text-[var(--muted-foreground)] text-xs p-6 rounded-xl border border-[var(--surface-border)] text-center">
    Loading templates...
  </div>

  <div v-else class="flex flex-col md:flex-row gap-4">
    <!-- Template list -->
    <div class="md:w-48 flex-shrink-0">
      <div class="space-y-0.5">
        <button
          v-for="t in templateList"
          :key="t.id"
          @click="selectedId = t.id"
          class="w-full text-left px-3 py-2 rounded-lg text-[10px] transition-colors"
          :class="selectedId === t.id
            ? 'bg-[var(--surface)] text-[var(--foreground)] border border-[var(--surface-border-hover)]'
            : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--surface-skeleton)]'"
        >
          <span class="mr-1">{{ templateIcons[t.id] || '📋' }}</span>
          {{ t.name }}
        </button>
      </div>
    </div>

    <!-- Editor area -->
    <div class="flex-1 min-w-0 space-y-3">
      <!-- Template info -->
      <div>
        <h3 class="text-sm font-semibold">{{ templates[selectedId]?.name }}</h3>
        <p class="text-[10px] text-[var(--muted-foreground)] mt-0.5">{{ templates[selectedId]?.description }}</p>
      </div>

      <!-- Variable chips -->
      <div>
        <span class="text-[9px] text-[var(--muted-foreground)] uppercase tracking-wide">Variables</span>
        <div class="flex flex-wrap gap-1 mt-1">
          <button
            v-for="v in variables"
            :key="v"
            @click="insertVariable(v)"
            class="text-[9px] px-1.5 py-0.5 rounded bg-[var(--accent-warm-muted)] text-[var(--accent-warm)] hover:opacity-80 transition-opacity font-mono"
          >
            {{ varChip(v) }}
          </button>
        </div>
      </div>

      <!-- Textarea -->
      <div class="relative">
        <textarea
          data-template-editor
          :value="draft"
          @input="onEdit(($event.target as HTMLTextAreaElement).value)"
          :maxlength="2000"
          rows="8"
          class="w-full px-3 py-2.5 rounded-xl text-[11px] font-mono leading-relaxed bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] outline-none focus:border-[var(--surface-border-hover)] resize-y transition-colors"
          placeholder="Edit template..."
        />
        <span class="absolute bottom-2 right-3 text-[9px] text-[var(--muted-foreground)] tabular-nums">{{ draft.length }}/2000</span>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-2">
        <button
          @click="generatePreview"
          class="h-7 px-3 rounded-lg text-[10px] font-medium bg-[var(--surface)] border border-[var(--surface-border)] text-[var(--foreground)] hover:border-[var(--surface-border-hover)] transition-colors"
        >
          Preview
        </button>
        <button
          @click="handleTest"
          :disabled="sending"
          class="h-7 px-3 rounded-lg text-[10px] font-medium transition-colors"
          :class="sending
            ? 'bg-[var(--surface-skeleton)] text-[var(--muted-foreground)] cursor-wait'
            : 'bg-[var(--accent-warm)] text-[var(--primary-foreground)] hover:opacity-90'"
        >
          {{ sending ? 'Sending...' : 'Send Test' }}
        </button>
        <button
          @click="handleReset"
          class="h-7 px-3 rounded-lg text-[10px] font-medium border transition-colors"
          :class="confirmingReset
            ? 'bg-[var(--badge-sell)] border-[var(--border-sell)] text-[var(--bearish)]'
            : 'border-[var(--surface-border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[var(--surface-border-hover)]'"
        >
          {{ confirmingReset ? 'Confirm Reset?' : 'Reset to Default' }}
        </button>
        <span v-if="testResult" class="text-[10px] ml-2" :class="testResult.sent ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'">
          {{ testResult.sent ? 'Sent' : 'Failed' }}
        </span>
      </div>

      <!-- Preview bubble -->
      <TelegramMessagePreview v-if="previewText" :message="previewText" :parse-mode="settings?.parse_mode" />
    </div>
  </div>
</template>
