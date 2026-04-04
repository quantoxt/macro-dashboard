<script setup lang="ts">
const publicCommands = [
  { cmd: '/start', desc: 'Welcome + auto-subscribe' },
  { cmd: '/subscribe', desc: 'Subscribe to signal notifications' },
  { cmd: '/unsubscribe', desc: 'Unsubscribe from signal notifications' },
  { cmd: '/signals', desc: 'View active signals' },
  { cmd: '/status', desc: 'Engine status (VIX, signals, refresh)' },
  { cmd: '/brief', desc: 'Market overview (session, VIX, counts)' },
  { cmd: '/check <instrument>', desc: 'Check signals for a specific instrument' },
  { cmd: '/help', desc: 'Show available commands' },
]

const ownerCommands = [
  { cmd: '/pause', desc: 'Pause all notifications' },
  { cmd: '/resume', desc: 'Resume notifications' },
  { cmd: '/settings', desc: 'View notification settings' },
  { cmd: '/history', desc: 'Last 5 resolved signals' },
  { cmd: '/subscribers', desc: 'View subscriber list' },
  { cmd: '/broadcast <message>', desc: 'Send message to all subscribers (60s cooldown)' },
]
</script>

<template>
  <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4">
    <!-- Public Commands -->
    <div class="mb-4">
      <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-3 flex items-center gap-2">
        <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
        Public Commands
        <span class="text-[10px] px-1.5 py-0.5 rounded-md bg-[var(--surface-skeleton)] text-[var(--muted-foreground)] font-normal normal-case tracking-normal">
          Everyone
        </span>
      </h3>
      <div class="space-y-1.5">
        <div v-for="c in publicCommands" :key="c.cmd" class="flex items-start gap-2">
          <code class="text-[10px] font-mono text-[var(--accent-warm)] whitespace-nowrap flex-shrink-0">{{ c.cmd }}</code>
          <span class="text-[10px] text-[var(--muted-foreground)]">{{ c.desc }}</span>
        </div>
      </div>
    </div>

    <!-- Divider -->
    <div class="border-b border-[var(--surface-border)] mb-4" />

    <!-- Owner Commands -->
    <div>
      <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-3 flex items-center gap-2">
        <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
        Owner Commands
        <span class="text-[10px] px-1.5 py-0.5 rounded-md bg-[var(--accent-warm)] text-[var(--primary-foreground)] font-normal normal-case tracking-normal">
          Owner Only
        </span>
      </h3>
      <div class="space-y-1.5">
        <div v-for="c in ownerCommands" :key="c.cmd" class="flex items-start gap-2">
          <code class="text-[10px] font-mono text-[var(--accent-warm)] whitespace-nowrap flex-shrink-0">{{ c.cmd }}</code>
          <span class="text-[10px] text-[var(--muted-foreground)]">{{ c.desc }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
