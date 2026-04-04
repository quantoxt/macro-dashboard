<script setup lang="ts">
import { useTelegram } from '~/composables/useTelegram'

const { settings, updateSettings } = useTelegram()

function toggleChat(idx: number) {
  if (!settings.value) return
  const chats = [...settings.value.chats]
  chats[idx] = { ...chats[idx], enabled: !chats[idx].enabled }
  updateSettings({ chats })
}

function addChat() {
  if (!settings.value) return
  const label = `Chat ${settings.value.chats.length + 1}`
  const chats = [...settings.value.chats, { id: '', label, enabled: true }]
  updateSettings({ chats })
}

function removeChat(idx: number) {
  if (!settings.value) return
  if (settings.value.chats.length <= 1) return
  const chats = settings.value.chats.filter((_, i) => i !== idx)
  updateSettings({ chats })
}

function updateChatField(idx: number, field: 'id' | 'label', value: string) {
  if (!settings.value) return
  const chats = [...settings.value.chats]
  chats[idx] = { ...chats[idx], [field]: value }
  updateSettings({ chats })
}

function maskedId(id: string): string {
  if (!id || id.length < 8) return id || '--'
  return id.slice(0, 4) + '***' + id.slice(-4)
}
</script>

<template>
  <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
        <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
        Chat Destinations
      </h3>
      <button
        class="text-[10px] px-2.5 py-1 rounded-lg bg-[var(--accent-warm)] text-[var(--primary-foreground)] font-medium hover:opacity-90 transition-opacity"
        @click="addChat"
      >
        + Add Chat
      </button>
    </div>

    <div v-if="settings?.chats?.length" class="space-y-2">
      <div
        v-for="(chat, idx) in settings.chats"
        :key="idx"
        class="flex items-center gap-3 px-3 py-2 rounded-lg border border-[var(--surface-border)] bg-[var(--surface-skeleton)]"
      >
        <!-- Toggle -->
        <button
          class="relative w-9 h-5 rounded-full transition-all duration-200 flex-shrink-0"
          :class="chat.enabled ? 'bg-[var(--bullish)]' : 'bg-[var(--bearish)]'"
          @click="toggleChat(idx)"
        >
          <span
            class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200"
            :class="chat.enabled ? 'translate-x-4' : 'translate-x-0'"
          />
        </button>

        <!-- Label -->
        <input
          :value="chat.label"
          @input="updateChatField(idx, 'label', ($event.target as HTMLInputElement).value)"
          class="text-[10px] w-20 px-1.5 py-0.5 rounded bg-transparent border border-transparent hover:border-[var(--surface-border)] focus:border-[var(--surface-border-hover)] outline-none text-[var(--foreground)]"
        />

        <!-- Chat ID -->
        <input
          :value="chat.id"
          @input="updateChatField(idx, 'id', ($event.target as HTMLInputElement).value)"
          :placeholder="maskedId(chat.id) || 'Chat ID'"
          class="text-[10px] flex-1 px-1.5 py-0.5 rounded bg-transparent border border-transparent hover:border-[var(--surface-border)] focus:border-[var(--surface-border-hover)] outline-none text-[var(--muted-foreground)] font-mono"
        />

        <!-- Remove -->
        <button
          v-if="settings.chats.length > 1"
          class="text-[10px] text-[var(--muted-foreground)] hover:text-[var(--bearish)] transition-colors flex-shrink-0"
          @click="removeChat(idx)"
        >
          Remove
        </button>
      </div>
    </div>

    <div v-else class="text-[10px] text-[var(--muted-foreground)] text-center py-3">
      No chats configured
    </div>
  </div>
</template>
