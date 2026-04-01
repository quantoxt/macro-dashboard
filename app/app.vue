<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
useHead({
  title: 'Macro Dashboard',
  meta: [
    { name: 'description', content: 'Forex macro confluence dashboard — yield spreads, multi-timeframe scoring, and institutional-grade market analysis.' },
    { name: 'theme-color', content: '#1a1a1f' },
    { name: 'color-scheme', content: 'dark' },
    { property: 'og:title', content: 'Macro Dashboard' },
    { property: 'og:description', content: 'Forex macro confluence dashboard — yield spreads, multi-timeframe scoring, and institutional-grade market analysis.' },
    { property: 'og:type', content: 'website' },
  ],
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
  ],
})
</script>
