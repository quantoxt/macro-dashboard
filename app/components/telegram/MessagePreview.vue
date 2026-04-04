<script setup lang="ts">
defineProps<{
  message: string
  parseMode?: 'markdown' | 'plain'
}>()
</script>

<template>
  <div class="mt-3">
    <span class="text-[9px] text-[var(--muted-foreground)] uppercase tracking-wide">Preview</span>
    <div class="mt-1 max-w-[400px] rounded-xl rounded-tl-sm px-3.5 py-2.5 text-[11px] leading-relaxed whitespace-pre-wrap"
      style="background: rgba(16, 185, 129, 0.06); border: 1px solid rgba(16, 185, 129, 0.12);"
    >
      {{ message || 'No preview yet' }}
    </div>
  </div>
</template>
