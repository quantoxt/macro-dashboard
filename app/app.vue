<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
onMounted(() => {
  if (import.meta.client) {
    import('lenis').then(({ default: Lenis }) => {
      const lenis = new Lenis({
        duration: 1.5,
        easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
        syncTouch: true,
        touchMultiplier: 2,
      })

      function raf(time: number) {
        lenis.raf(time)
        requestAnimationFrame(raf)
      }

      requestAnimationFrame(raf)
    })
  }
})

useHead({
  title: 'Macro Dashboard',
  meta: [
    { name: 'description', content: 'Forex macro confluence dashboard — yield spreads, multi-timeframe scoring, and institutional-grade market analysis.' },
    { name: 'theme-color', content: '#07070d' },
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
