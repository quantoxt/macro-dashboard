<script setup lang="ts">
interface Subscriber {
  chat_id: string
  label: string
  chat_type: string
  active: boolean
  subscribed_at: string
  unsubscribed_at: string | null
}

const subscribers = ref<Subscriber[]>([])
const activeCount = ref(0)
const totalCount = ref(0)
const loading = ref(true)
const broadcastMessage = ref('')
const broadcastSending = ref(false)
const broadcastCooldown = ref(0)
const broadcastResult = ref<{ sent: number; failed: number } | null>(null)
const removingId = ref<string | null>(null)

// Pagination & filters
const currentPage = ref(1)
const perPage = ref(25)
const searchQuery = ref('')
const statusFilter = ref<'all' | 'active' | 'inactive'>('all')
const perPageOptions = [10, 25, 50, 100]

let cooldownInterval: ReturnType<typeof setInterval> | null = null
let resultTimeout: ReturnType<typeof setTimeout> | null = null
let pollInterval: ReturnType<typeof setInterval> | null = null

function maskedId(id: string): string {
  if (!id || id.length < 8) return id || '--'
  return id.slice(0, 4) + '***' + id.slice(-4)
}

function relativeTime(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = now - then

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const weeks = Math.floor(days / 7)

  if (seconds < 60) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  return `${weeks}w ago`
}

// Metrics from full dataset
const churnedCount = computed(() => totalCount.value - activeCount.value)
const groupCount = computed(() => subscribers.value.filter(s => s.active && s.chat_type !== 'private').length)
const dmCount = computed(() => subscribers.value.filter(s => s.active && s.chat_type === 'private').length)

// Full sorted list
const sortedSubscribers = computed(() =>
  [...subscribers.value].sort((a, b) => {
    if (a.active !== b.active) return a.active ? -1 : 1
    return new Date(b.subscribed_at).getTime() - new Date(a.subscribed_at).getTime()
  })
)

// Filtered list (search + status)
const filteredSubscribers = computed(() => {
  let list = sortedSubscribers.value

  if (statusFilter.value === 'active') list = list.filter(s => s.active)
  else if (statusFilter.value === 'inactive') list = list.filter(s => !s.active)

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(s =>
      (s.label || '').toLowerCase().includes(q)
      || s.chat_id.toLowerCase().includes(q)
      || s.chat_type.toLowerCase().includes(q)
    )
  }

  return list
})

// Pagination
const totalPages = computed(() => Math.max(1, Math.ceil(filteredSubscribers.value.length / perPage.value)))

const paginatedSubscribers = computed(() => {
  const start = (currentPage.value - 1) * perPage.value
  return filteredSubscribers.value.slice(start, start + perPage.value)
})

const pageNumbers = computed(() => {
  const pages: number[] = []
  const total = totalPages.value
  const current = currentPage.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    if (current > 3) pages.push(-1) // ellipsis
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i)
    if (current < total - 2) pages.push(-1) // ellipsis
    pages.push(total)
  }
  return pages
})

// Reset to page 1 when filters change
watch([searchQuery, statusFilter, perPage], () => {
  currentPage.value = 1
})

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

async function fetchSubscribers() {
  try {
    const res = await $fetch<{ subscribers: Subscriber[]; active_count: number; total_count: number }>('/api/telegram-subscribers')
    subscribers.value = res.subscribers
    activeCount.value = res.active_count
    totalCount.value = res.total_count
  } catch {
    // silently fail — UI shows whatever was last loaded
  } finally {
    loading.value = false
  }
}

async function removeSubscriber(chatId: string) {
  try {
    await $fetch('/api/telegram-subscribers', {
      method: 'DELETE',
      body: { chat_id: chatId },
    })
    await fetchSubscribers()
  } catch {
    // keep UI stable on error
  }
  removingId.value = null
}

async function sendBroadcast() {
  const msg = broadcastMessage.value.trim()
  if (!msg || broadcastSending.value || broadcastCooldown.value > 0) return

  broadcastSending.value = true
  try {
    const res = await $fetch<{ sent: number; failed: number; total: number }>('/api/telegram-broadcast', {
      method: 'POST',
      body: { message: msg },
    })
    broadcastResult.value = { sent: res.sent, failed: res.failed }
    broadcastMessage.value = ''
    startCooldown()
  } catch {
    broadcastResult.value = { sent: 0, failed: -1 }
  }
  broadcastSending.value = false

  if (resultTimeout) clearTimeout(resultTimeout)
  resultTimeout = setTimeout(() => { broadcastResult.value = null }, 5000)
}

function startCooldown() {
  broadcastCooldown.value = 60
  if (cooldownInterval) clearInterval(cooldownInterval)
  cooldownInterval = setInterval(() => {
    broadcastCooldown.value--
    if (broadcastCooldown.value <= 0) {
      broadcastCooldown.value = 0
      if (cooldownInterval) clearInterval(cooldownInterval)
      cooldownInterval = null
    }
  }, 1000)
}

function confirmRemove(chatId: string) {
  removingId.value = chatId
}

function cancelRemove() {
  removingId.value = null
}

onMounted(() => {
  fetchSubscribers()
  pollInterval = setInterval(fetchSubscribers, 30000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (cooldownInterval) clearInterval(cooldownInterval)
  if (resultTimeout) clearTimeout(resultTimeout)
})
</script>

<template>
  <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4">
    <!-- Header + Refresh -->
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase flex items-center gap-2">
        <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
        Subscribers
      </h3>
      <button
        class="text-[10px] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
        @click="fetchSubscribers"
      >
        Refresh ↻
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-2 mb-4">
      <div class="h-8 rounded-lg shimmer bg-[var(--surface-skeleton)]" />
      <div class="h-6 rounded-lg shimmer bg-[var(--surface-skeleton)]" />
    </div>

    <template v-else>
      <!-- Metrics bar -->
      <div class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-[10px] px-2 py-0.5 rounded-md bg-[var(--surface-skeleton)] text-[var(--bullish)] font-medium">
          {{ activeCount }} Active
        </span>
        <span class="text-[10px] px-2 py-0.5 rounded-md bg-[var(--surface-skeleton)] text-[var(--muted-foreground)]">
          {{ totalCount }} Total
        </span>
        <span v-if="churnedCount > 0" class="text-[10px] px-2 py-0.5 rounded-md bg-[var(--surface-skeleton)] text-[var(--bearish)]">
          {{ churnedCount }} Churned
        </span>
        <span class="text-[10px] text-[var(--muted-foreground)]">
          ├─ 👤 {{ dmCount }} DMs
        </span>
        <span class="text-[10px] text-[var(--muted-foreground)]">
          ├─ 👥 {{ groupCount }} Group{{ groupCount !== 1 ? 's' : '' }}
        </span>
      </div>

      <!-- Filters bar -->
      <div class="flex flex-wrap items-center gap-2 mb-3">
        <!-- Search -->
        <div class="relative flex-1 min-w-[140px]">
          <input
            v-model="searchQuery"
            placeholder="Search name or ID..."
            class="w-full text-[10px] px-2.5 py-1.5 pl-6 rounded-lg bg-[var(--surface-skeleton)] border border-[var(--surface-border)] outline-none text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--surface-border-hover)] transition-colors"
          />
          <span class="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-[var(--muted-foreground)]">⌕</span>
        </div>

        <!-- Status filter -->
        <div class="flex rounded-lg border border-[var(--surface-border)] overflow-hidden">
          <button
            v-for="opt in (['all', 'active', 'inactive'] as const)"
            :key="opt"
            class="text-[10px] px-2.5 py-1 transition-colors"
            :class="statusFilter === opt
              ? 'bg-[var(--accent-warm)] text-[var(--primary-foreground)]'
              : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
            @click="statusFilter = opt"
          >
            {{ opt === 'all' ? 'All' : opt === 'active' ? 'Active' : 'Inactive' }}
          </button>
        </div>

        <!-- Per page -->
        <select
          v-model.number="perPage"
          class="text-[10px] px-2 py-1 rounded-lg bg-[var(--surface-skeleton)] border border-[var(--surface-border)] outline-none text-[var(--muted-foreground)] cursor-pointer"
        >
          <option v-for="n in perPageOptions" :key="n" :value="n">{{ n }}/page</option>
        </select>
      </div>

      <!-- Subscriber list -->
      <div v-if="paginatedSubscribers.length" class="space-y-1.5 mb-3">
        <div
          v-for="sub in paginatedSubscribers"
          :key="sub.chat_id"
          class="px-3 py-2 rounded-lg border border-[var(--surface-border)] bg-[var(--surface-skeleton)]"
          :class="!sub.active ? 'opacity-50' : ''"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1.5">
              <span class="text-[10px]">{{ sub.active ? '✅' : '❌' }}</span>
              <span class="text-[10px]">{{ sub.chat_type === 'private' ? '👤' : '👥' }}</span>
              <span class="text-[10px] text-[var(--foreground)] font-medium">{{ sub.label || 'Unknown' }}</span>
            </div>
            <!-- Remove / Confirm -->
            <template v-if="removingId === sub.chat_id">
              <div class="flex items-center gap-1.5">
                <button
                  class="text-[10px] text-[var(--bearish)] hover:underline"
                  @click="removeSubscriber(sub.chat_id)"
                >
                  Yes
                </button>
                <button
                  class="text-[10px] text-[var(--muted-foreground)] hover:underline"
                  @click="cancelRemove"
                >
                  No
                </button>
              </div>
            </template>
            <template v-else>
              <button
                class="text-[10px] text-[var(--muted-foreground)] hover:text-[var(--bearish)] transition-colors"
                @click="confirmRemove(sub.chat_id)"
              >
                ×
              </button>
            </template>
          </div>
          <div class="flex items-center gap-1.5 mt-0.5">
            <span class="text-[10px] text-[var(--muted-foreground)] font-mono">{{ maskedId(sub.chat_id) }}</span>
            <span class="text-[10px] text-[var(--muted-foreground)]">·</span>
            <span class="text-[10px] text-[var(--muted-foreground)]">{{ sub.chat_type }}</span>
            <span class="text-[10px] text-[var(--muted-foreground)]">·</span>
            <span class="text-[10px] text-[var(--muted-foreground)]">
              {{ sub.active ? relativeTime(sub.subscribed_at) : 'unsubscribed' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="text-[10px] text-[var(--muted-foreground)] text-center py-3 mb-3">
        {{ searchQuery || statusFilter !== 'all' ? 'No subscribers match filters' : 'No subscribers yet' }}
      </div>

      <!-- Pagination controls -->
      <div v-if="totalPages > 1" class="flex items-center justify-between mb-4">
        <span class="text-[10px] text-[var(--muted-foreground)]">
          {{ filteredSubscribers.length }} result{{ filteredSubscribers.length !== 1 ? 's' : '' }}
        </span>
        <div class="flex items-center gap-1">
          <button
            :disabled="currentPage <= 1"
            class="text-[10px] px-2 py-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            @click="goToPage(currentPage - 1)"
          >
            ‹ Prev
          </button>
          <template v-for="page in pageNumbers" :key="page">
            <span v-if="page === -1" class="text-[10px] text-[var(--muted-foreground)] px-1">…</span>
            <button
              v-else
              class="text-[10px] w-6 h-6 rounded-md transition-colors"
              :class="page === currentPage
                ? 'bg-[var(--accent-warm)] text-[var(--primary-foreground)] font-medium'
                : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
          </template>
          <button
            :disabled="currentPage >= totalPages"
            class="text-[10px] px-2 py-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            @click="goToPage(currentPage + 1)"
          >
            Next ›
          </button>
        </div>
      </div>

      <!-- Broadcast section -->
      <div class="border-t border-[var(--surface-border)] pt-3">
        <h4 class="text-[10px] font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-2">
          Broadcast
        </h4>
        <div class="flex items-center gap-2">
          <input
            v-model="broadcastMessage"
            :disabled="broadcastCooldown > 0 || activeCount === 0"
            placeholder="Type a message..."
            class="flex-1 text-[10px] px-2.5 py-1.5 rounded-lg bg-[var(--surface-skeleton)] border border-[var(--surface-border)] outline-none text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--surface-border-hover)] transition-colors disabled:opacity-50"
            @keydown.enter="sendBroadcast"
          />
          <button
            :disabled="!broadcastMessage.trim() || broadcastCooldown > 0 || broadcastSending || activeCount === 0"
            class="text-[10px] px-3 py-1.5 rounded-lg bg-[var(--accent-warm)] text-[var(--primary-foreground)] font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            @click="sendBroadcast"
          >
            {{ broadcastSending ? 'Sending...' : 'Send ▶' }}
          </button>
        </div>

        <!-- Cooldown -->
        <div v-if="broadcastCooldown > 0" class="text-[10px] text-[var(--muted-foreground)] mt-1.5">
          Cooldown: {{ broadcastCooldown }}s
        </div>

        <!-- No active subscribers -->
        <div v-if="activeCount === 0 && !loading" class="text-[10px] text-[var(--muted-foreground)] mt-1.5">
          No active subscribers
        </div>

        <!-- Result -->
        <div v-if="broadcastResult" class="text-[10px] mt-1.5">
          <span v-if="broadcastResult.failed === -1" class="text-[var(--bearish)]">
            ⚠ Broadcast failed
          </span>
          <span v-else class="text-[var(--bullish)]">
            ✅ Sent to {{ broadcastResult.sent }} subscriber{{ broadcastResult.sent !== 1 ? 's' : '' }}
            <span v-if="broadcastResult.failed > 0" class="text-[var(--bearish)]"> · ⚠ {{ broadcastResult.failed }} failed</span>
          </span>
        </div>
      </div>
    </template>
  </div>
</template>
