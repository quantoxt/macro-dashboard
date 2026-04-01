// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: [
    '@nuxt/eslint',
    '@nuxtjs/tailwindcss',
    'shadcn-nuxt',
  ],

  css: [
    "./app/assets/css/tailwind.css",
  ],

  shadcn: {
    prefix: '',
    componentDir: './app/components/ui'
  },

  runtimeConfig: {
    fredApiKey: '',
  },
})
