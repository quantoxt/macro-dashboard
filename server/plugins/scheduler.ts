import { $fetch } from 'ofetch'

export default defineNitroPlugin(() => {
  const base = `http://localhost:${process.env.PORT || 3000}`

  // Initial fetch on startup — delay 3s to let server be ready
  setTimeout(async () => {
    console.log('[Scheduler] Running initial data fetch...')
    try {
      await Promise.all([
        $fetch(`${base}/api/_cron/update-yields`),
        $fetch(`${base}/api/_cron/update-heatmap`),
      ])
      console.log('[Scheduler] Initial fetch complete')
    }
    catch (err) {
      console.error('[Scheduler] Initial fetch failed:', err)
    }
  }, 3000)

  // Yield spreads: every 30 min
  setInterval(async () => {
    try {
      await $fetch(`${base}/api/_cron/update-yields`)
    }
    catch (err) {
      console.error('[Scheduler] Yield update failed:', err)
    }
  }, 30 * 60 * 1000)

  // Heatmap: every 15 min
  setInterval(async () => {
    try {
      await $fetch(`${base}/api/_cron/update-heatmap`)
    }
    catch (err) {
      console.error('[Scheduler] Heatmap update failed:', err)
    }
  }, 15 * 60 * 1000)

  console.log('[Scheduler] Cron jobs registered')
})
