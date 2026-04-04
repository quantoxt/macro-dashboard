<script setup lang="ts">
import { useTelegram } from '~/composables/useTelegram'

const { settings, updateSettings } = useTelegram()

function toggle(field: keyof typeof settings.value) {
  if (!settings.value) return
  updateSettings({ [field]: !settings.value[field] })
}

const instruments = ['XAUUSD', 'XAGUSD', 'USDJPY', 'GBPJPY', 'BTCUSD']
const strategyLabels: Record<string, string> = {
  confluence_breakout: 'Confluence Breakout',
  mean_reversion: 'Mean Reversion',
  momentum_shift: 'Momentum Shift',
}

function toggleInstrument(inst: string) {
  if (!settings.value) return
  const map = { ...settings.value.instrument_notifications }
  map[inst] = !map[inst]
  updateSettings({ instrument_notifications: map })
}

function toggleStrategy(strat: string) {
  if (!settings.value) return
  const map = { ...settings.value.strategy_notifications }
  map[strat] = !map[strat]
  updateSettings({ strategy_notifications: map })
}
</script>

<template>
  <div v-if="settings" class="space-y-4">

    <!-- General -->
    <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 space-y-3">
      <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
        <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
        General
      </h3>

      <div class="flex items-center justify-between">
        <span class="text-xs text-[var(--foreground)]">Parse Mode</span>
        <select
          :value="settings.parse_mode"
          @change="updateSettings({ parse_mode: ($event.target as HTMLSelectElement).value as 'markdown' | 'plain' })"
          class="h-7 px-2 rounded-lg text-[10px] font-medium bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none"
        >
          <option value="markdown">Markdown</option>
          <option value="plain">Plain Text</option>
        </select>
      </div>

      <div class="flex items-center justify-between">
        <span class="text-xs text-[var(--foreground)]">Batch Window</span>
        <div class="flex items-center gap-2">
          <input
            type="number"
            :value="settings.batch_window"
            @change="updateSettings({ batch_window: Number(($event.target as HTMLInputElement).value) })"
            min="0"
            max="300"
            class="w-16 h-7 px-2 rounded-lg text-[10px] text-center bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none tabular-nums"
          />
          <span class="text-[9px] text-[var(--muted-foreground)]">sec</span>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <span class="text-xs text-[var(--foreground)]">TradingView Links</span>
        <button
          class="relative w-9 h-5 rounded-full transition-all duration-200"
          :class="settings.tradingview_links ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
          @click="toggle('tradingview_links')"
        >
          <span
            class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200"
            :class="settings.tradingview_links ? 'translate-x-4' : 'translate-x-0'"
          />
        </button>
      </div>
    </div>

    <!-- Signal Alerts -->
    <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 space-y-3">
      <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
        <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
        Signal Alerts
      </h3>

      <div class="flex items-center justify-between">
        <span class="text-xs text-[var(--foreground)]">Min Confidence</span>
        <div class="flex items-center gap-2">
          <input
            type="range"
            :value="settings.min_confidence"
            @input="updateSettings({ min_confidence: Number(($event.target as HTMLInputElement).value) })"
            min="0"
            max="100"
            step="5"
            class="w-24 accent-[var(--accent-warm)]"
          />
          <span class="text-[10px] tabular-nums text-[var(--foreground)] w-8 text-right">{{ settings.min_confidence }}%</span>
        </div>
      </div>

      <!-- Per-instrument -->
      <div>
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase tracking-wide">Instruments</span>
        <div class="mt-1.5 flex flex-wrap gap-2">
          <button
            v-for="inst in instruments"
            :key="inst"
            @click="toggleInstrument(inst)"
            class="text-[10px] px-2.5 py-1 rounded-lg border transition-colors font-medium"
            :class="settings.instrument_notifications[inst] !== false
              ? 'bg-[var(--badge-buy)] border-[var(--border-buy)] text-[var(--bullish)]'
              : 'bg-[var(--surface-skeleton)] border-[var(--surface-border)] text-[var(--muted-foreground)]'"
          >
            {{ inst }}
          </button>
        </div>
      </div>

      <!-- Per-strategy -->
      <div>
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase tracking-wide">Strategies</span>
        <div class="mt-1.5 flex flex-wrap gap-2">
          <button
            v-for="(label, key) in strategyLabels"
            :key="key"
            @click="toggleStrategy(key)"
            class="text-[10px] px-2.5 py-1 rounded-lg border transition-colors font-medium"
            :class="settings.strategy_notifications[key] !== false
              ? 'bg-[var(--badge-buy)] border-[var(--border-buy)] text-[var(--bullish)]'
              : 'bg-[var(--surface-skeleton)] border-[var(--surface-border)] text-[var(--muted-foreground)]'"
          >
            {{ label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Outcome Alerts -->
    <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 space-y-3">
      <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
        <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
        Outcome Alerts
      </h3>

      <div class="flex items-center justify-between">
        <span class="text-xs text-[var(--foreground)]">Enable Outcome Alerts</span>
        <button
          class="relative w-9 h-5 rounded-full transition-all duration-200"
          :class="settings.outcome_alerts ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
          @click="toggle('outcome_alerts')"
        >
          <span
            class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200"
            :class="settings.outcome_alerts ? 'translate-x-4' : 'translate-x-0'"
          />
        </button>
      </div>

      <div class="space-y-2 pl-2 transition-opacity" :class="settings.outcome_alerts ? 'opacity-100' : 'opacity-30 pointer-events-none'">
        <div class="flex items-center justify-between">
          <span class="text-xs text-[var(--bullish)]">WIN Alerts</span>
          <button
            class="relative w-9 h-5 rounded-full transition-all duration-200"
            :class="settings.outcome_win ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
            @click="toggle('outcome_win')"
          >
            <span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200" :class="settings.outcome_win ? 'translate-x-4' : 'translate-x-0'" />
          </button>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-[var(--bearish)]">LOSS Alerts</span>
          <button
            class="relative w-9 h-5 rounded-full transition-all duration-200"
            :class="settings.outcome_loss ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
            @click="toggle('outcome_loss')"
          >
            <span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200" :class="settings.outcome_loss ? 'translate-x-4' : 'translate-x-0'" />
          </button>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-[var(--muted-foreground)]">EXPIRED Alerts</span>
          <button
            class="relative w-9 h-5 rounded-full transition-all duration-200"
            :class="settings.outcome_expired ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
            @click="toggle('outcome_expired')"
          >
            <span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200" :class="settings.outcome_expired ? 'translate-x-4' : 'translate-x-0'" />
          </button>
        </div>
      </div>
    </div>

    <!-- Quiet Hours -->
    <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
          <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
          Quiet Hours
        </h3>
        <button
          class="relative w-9 h-5 rounded-full transition-all duration-200"
          :class="settings.quiet_hours_enabled ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
          @click="toggle('quiet_hours_enabled')"
        >
          <span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200" :class="settings.quiet_hours_enabled ? 'translate-x-4' : 'translate-x-0'" />
        </button>
      </div>

      <div class="flex items-center gap-3 transition-opacity" :class="settings.quiet_hours_enabled ? 'opacity-100' : 'opacity-30 pointer-events-none'">
        <div class="flex items-center gap-2">
          <span class="text-[10px] text-[var(--muted-foreground)]">From</span>
          <input
            type="time"
            :value="settings.quiet_hours_start"
            @change="updateSettings({ quiet_hours_start: ($event.target as HTMLInputElement).value })"
            class="h-7 px-2 rounded-lg text-[10px] bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none"
          />
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[10px] text-[var(--muted-foreground)]">To</span>
          <input
            type="time"
            :value="settings.quiet_hours_end"
            @change="updateSettings({ quiet_hours_end: ($event.target as HTMLInputElement).value })"
            class="h-7 px-2 rounded-lg text-[10px] bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none"
          />
        </div>
      </div>
    </div>

    <!-- Cooldown -->
    <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
          <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
          Cooldown
        </h3>
        <button
          class="relative w-9 h-5 rounded-full transition-all duration-200"
          :class="settings.cooldown_enabled ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
          @click="toggle('cooldown_enabled')"
        >
          <span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200" :class="settings.cooldown_enabled ? 'translate-x-4' : 'translate-x-0'" />
        </button>
      </div>

      <div class="flex items-center justify-between transition-opacity" :class="settings.cooldown_enabled ? 'opacity-100' : 'opacity-30 pointer-events-none'">
        <span class="text-xs text-[var(--foreground)]">Duration</span>
        <div class="flex items-center gap-2">
          <input
            type="number"
            :value="settings.cooldown_hours"
            @change="updateSettings({ cooldown_hours: Number(($event.target as HTMLInputElement).value) })"
            min="0.5"
            max="48"
            step="0.5"
            class="w-16 h-7 px-2 rounded-lg text-[10px] text-center bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none tabular-nums"
          />
          <span class="text-[9px] text-[var(--muted-foreground)]">hours</span>
        </div>
      </div>
    </div>

    <!-- Daily Summary -->
    <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4 space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
          <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
          Daily Summary
        </h3>
        <button
          class="relative w-9 h-5 rounded-full transition-all duration-200"
          :class="settings.daily_summary_enabled ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
          @click="toggle('daily_summary_enabled')"
        >
          <span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200" :class="settings.daily_summary_enabled ? 'translate-x-4' : 'translate-x-0'" />
        </button>
      </div>

      <div class="flex items-center justify-between transition-opacity" :class="settings.daily_summary_enabled ? 'opacity-100' : 'opacity-30 pointer-events-none'">
        <span class="text-xs text-[var(--foreground)]">Send at</span>
        <input
          type="time"
          :value="settings.daily_summary_time"
          @change="updateSettings({ daily_summary_time: ($event.target as HTMLInputElement).value })"
          class="h-7 px-2 rounded-lg text-[10px] bg-[var(--surface-skeleton)] border border-[var(--surface-border)] text-[var(--foreground)] outline-none"
        />
      </div>
    </div>
  </div>

  <div v-else class="text-[var(--muted-foreground)] text-xs p-6 rounded-xl border border-[var(--surface-border)] text-center">
    Loading settings...
  </div>
</template>
