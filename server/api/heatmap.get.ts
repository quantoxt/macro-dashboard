import { readStorage } from '../utils/storage'

export default defineEventHandler(async () => {
  const data = await readStorage<{
    instruments: any[]
    updatedAt: string | null
  }>('heatmap-cache.json', { instruments: [], updatedAt: null })

  return {
    updatedAt: data.updatedAt,
    instruments: data.instruments ?? [],
  }
})
