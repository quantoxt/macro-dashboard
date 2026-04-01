import { getHeatmapData } from '../utils/heatmap-service'

export default defineEventHandler(async () => {
  try {
    const data = await getHeatmapData()
    return {
      updatedAt: data.updatedAt,
      instruments: data.instruments ?? [],
    }
  }
  catch (err) {
    console.error('[Heatmap] Failed to fetch:', err)
    return {
      updatedAt: null,
      instruments: [],
    }
  }
})
