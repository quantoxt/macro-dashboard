<script setup lang="ts">
import { useStrategyConfig } from '@/composables/useStrategyConfig'
import { NumberField, NumberFieldContent, NumberFieldDecrement, NumberFieldIncrement, NumberFieldInput } from '@/components/ui/number-field'

const { configs, pending, error, saving, saveSuccess, updateStrategy, fetchConfig } = useStrategyConfig()

const strategyLabels: Record<string, string> = {
  confluence_breakout: 'Confluence Breakout',
  mean_reversion: 'Mean Reversion',
  momentum_shift: 'Momentum Shift',
}

// Snapshot initial values as defaults on first fetch
const defaults = ref<Record<string, Record<string, any>>>({})
watch(configs, (val) => {
  if (Object.keys(val).length && !Object.keys(defaults.value).length) {
    defaults.value = JSON.parse(JSON.stringify(val))
  }
}, { once: true })

function paramLabel(key: string): string {
  const labels: Record<string, string> = {
    enabled: 'Enabled',
    minConfidence: 'Min Confidence',
    minConfirmations: 'Min Confirmations',
    minRiskReward: 'Min R:R',
    atrSlMultiplier: 'ATR SL Multi',
    atrTpMultiplier: 'ATR TP Multi',
    rsiBuyThreshold: 'RSI Buy',
    rsiSellThreshold: 'RSI Sell',
  }
  return labels[key] || key
}

function paramStep(key: string): number {
  if (key.includes('confidence') || key.includes('Threshold')) return 5
  if (key.includes('Multiplier') || key.includes('RiskReward')) return 0.1
  if (key === 'minConfirmations') return 1
  return 1
}

function paramMin(key: string): number {
  if (key.includes('confidence') || key.includes('Threshold')) return 0
  if (key.includes('Multiplier') || key.includes('RiskReward')) return 0.1
  return 0
}

function paramMax(key: string): number {
  if (key.includes('confidence') || key.includes('Threshold')) return 100
  if (key.includes('Multiplier')) return 5
  if (key.includes('RiskReward')) return 10
  return 100
}

// Editable local copy per strategy
const edits = ref<Record<string, Record<string, any>>>({})

function getEdit(name: string, key: string): any {
  return edits.value[name]?.[key] ?? configs.value[name]?.[key as keyof typeof configs.value[string]] ?? null
}

function setEdit(name: string, key: string, val: any) {
  if (!edits.value[name]) edits.value[name] = {}
  edits.value[name][key] = val
}

async function handleSave(name: string) {
  const changes = edits.value[name]
  if (!changes) return
  await updateStrategy(name, changes)
  delete edits.value[name]
}

function isModified(name: string): boolean {
  const def = defaults.value[name]
  if (!def) return false
  const editsForStrategy = edits.value[name]
  if (editsForStrategy) {
    return Object.entries(editsForStrategy).some(([k, v]) => def[k] !== v)
  }
  return false
}

async function resetToDefault(name: string) {
  const def = defaults.value[name]
  if (!def) return
  // Set all edits to default values and save
  edits.value[name] = { ...def }
  await updateStrategy(name, { ...def })
}
</script>

<template>
  <div class="space-y-5">
    <h2 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Strategy Configuration
    </h2>

    <!-- Error -->
    <div v-if="error" class="text-[var(--bearish)] text-xs p-4 rounded-xl border border-[var(--border-sell)]">
      {{ error }}
    </div>

    <!-- Skeleton -->
    <template v-if="pending">
      <div class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-40 rounded-xl shimmer border border-[var(--surface-skeleton)]" />
      </div>
    </template>

    <!-- Strategy cards -->
    <template v-else>
      <div
        v-for="(config, name, idx) in configs"
        :key="name"
        class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 sm:px-5 space-y-4 transition-colors duration-200 hover:border-[var(--surface-border-hover)] anim-in"
        :style="{ animationDelay: (idx as number) * 100 + 'ms' }"
      >
        <!-- Header with toggle -->
        <div class="flex items-center justify-between">
          <span class="text-base font-semibold">{{ strategyLabels[name] || name }}</span>
          <button
            @click="setEdit(name, 'enabled', !getEdit(name, 'enabled')); handleSave(name)"
            class="relative w-11 h-6 rounded-full transition-all duration-200 active:scale-95"
            :class="getEdit(name, 'enabled') ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
            :aria-label="`Toggle ${strategyLabels[name] || name}`"
          >
            <span
              class="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200"
              :class="getEdit(name, 'enabled') ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
        </div>

        <!-- Parameters -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 transition-opacity duration-300" :class="getEdit(name, 'enabled') ? 'opacity-100' : 'opacity-30 pointer-events-none'">
          <template v-for="(value, key) in config" :key="key">
            <div v-if="key !== 'enabled'" class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
              <label class="text-xs text-[var(--muted-foreground)] sm:w-28 flex-shrink-0">{{ paramLabel(key as string) }}</label>
              <NumberField
                :model-value="getEdit(name, key as string)"
                @update:model-value="setEdit(name, key as string, $event)"
                :min="paramMin(key as string)"
                :max="paramMax(key as string)"
                :step="paramStep(key as string)"
                class="sm:flex-1"
              >
                <NumberFieldContent>
                  <NumberFieldDecrement />
                  <NumberFieldInput class="h-8 text-sm" />
                  <NumberFieldIncrement />
                </NumberFieldContent>
              </NumberField>
            </div>
          </template>
        </div>

        <!-- Save / Reset -->
        <div class="flex items-center gap-3 pt-1">
          <button
            @click="handleSave(name)"
            :disabled="saving || !getEdit(name, 'enabled')"
            class="px-3.5 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95"
            :class="saving
              ? 'bg-[var(--surface-skeleton)] text-[var(--muted-foreground)] cursor-wait'
              : 'bg-[var(--accent-warm)] text-[var(--primary-foreground)] hover:opacity-90'"
          >
            {{ saving ? 'Saving...' : 'Save Changes' }}
          </button>
          <button
            v-if="isModified(name)"
            @click="resetToDefault(name)"
            :disabled="saving"
            class="px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-200 border border-[var(--surface-border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[var(--surface-border-hover)] active:scale-95"
          >
            Reset to Default
          </button>
          <Transition name="saved" mode="out-in">
            <span v-if="saveSuccess === name" key="saved" class="text-xs text-[var(--bullish)]">Saved</span>
          </Transition>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!Object.keys(configs).length" class="text-[var(--muted-foreground)] text-xs p-6 rounded-xl border border-[var(--surface-border)] text-center">
        <p>No strategy configurations available</p>
        <p class="text-[10px] opacity-60 mt-1">Make sure the signal engine is running on port 8081.</p>
      </div>
    </template>
  </div>
</template>

<style>
@reference "tailwindcss";

.saved-enter-active {
  transition: all 200ms cubic-bezier(0.25, 1, 0.5, 1);
}
.saved-leave-active {
  transition: all 150ms cubic-bezier(0.25, 1, 0.5, 1);
}
.saved-enter-from,
.saved-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
