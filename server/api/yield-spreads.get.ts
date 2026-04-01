import { readStorage } from '../utils/storage'

export default defineEventHandler(async () => {
  const data = await readStorage<{
    buyCandidates: any[]
    sellCandidates: any[]
    updatedAt: string | null
  }>('yields.json', { buyCandidates: [], sellCandidates: [], updatedAt: null })

  return {
    updatedAt: data.updatedAt,
    buyCandidates: data.buyCandidates ?? [],
    sellCandidates: data.sellCandidates ?? [],
  }
})
