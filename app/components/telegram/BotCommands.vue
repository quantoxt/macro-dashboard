<script setup lang="ts">
const commands = [
  { cmd: '/signals', desc: 'View active signals' },
  { cmd: '/status', desc: 'Engine status' },
  { cmd: '/brief', desc: 'Market overview' },
  { cmd: '/check XAUUSD', desc: 'Check specific instrument' },
  { cmd: '/history', desc: 'Last 5 resolved signals' },
  { cmd: '/settings', desc: 'View notification settings' },
  { cmd: '/pause', desc: 'Pause notifications' },
  { cmd: '/resume', desc: 'Resume notifications' },
  { cmd: '/help', desc: 'Show commands' },
]
</script>

<template>
  <div class="border border-[var(--surface-border)] rounded-xl bg-[var(--surface)] px-4 py-4">
    <h3 class="text-xs font-medium tracking-wide text-[var(--muted-foreground)] uppercase mb-3 flex items-center gap-2">
      <span class="w-0.5 h-3 rounded-full bg-[var(--accent-warm)]" />
      Bot Commands
    </h3>
    <div class="space-y-1.5">
      <div v-for="c in commands" :key="c.cmd" class="flex items-start gap-2">
        <code class="text-[10px] font-mono text-[var(--accent-warm)] whitespace-nowrap flex-shrink-0">{{ c.cmd }}</code>
        <span class="text-[10px] text-[var(--muted-foreground)]">{{ c.desc }}</span>
      </div>
    </div>
  </div>
</template>
