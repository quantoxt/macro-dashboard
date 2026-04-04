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
    { name: 'color-scheme', content: 'dark light' },
    { property: 'og:title', content: 'Macro Dashboard' },
    { property: 'og:description', content: 'Forex macro confluence dashboard — yield spreads, multi-timeframe scoring, and institutional-grade market analysis.' },
    { property: 'og:type', content: 'website' },
  ],
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
  ],
  script: [
    {
      innerHTML: `(function(){try{var t=localStorage.getItem('macro-dashboard-theme');var d=document.documentElement;if(t==='light'){d.classList.add('light')}else if(t==='dark'){d.classList.add('dark')}else if(window.matchMedia('(prefers-color-scheme:light)').matches){d.classList.add('light')}else{d.classList.add('dark')}d.setAttribute('data-theme',d.classList.contains('light')?'light':'dark');var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute('content',d.classList.contains('light')?'#f4f5f9':'#07070d')}catch(e){}})()`,
      type: 'text/javascript',
      tagPosition: 'head',
    },
  ],
})
</script>
<style>
.page-enter-active,
.page-leave-active {
  transition: all 0.5s;
}

.page-enter-from,
.page-leave-to {
  opacity: 0;
  transform: translateY(10%);
}
</style>