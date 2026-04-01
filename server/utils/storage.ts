import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { join } from 'node:path'

const DATA_DIR = join(process.cwd(), 'server', 'data')

export async function readStorage<T>(filename: string, fallback: T): Promise<T> {
  try {
    const raw = await readFile(join(DATA_DIR, filename), 'utf-8')
    return JSON.parse(raw) as T
  }
  catch {
    return fallback
  }
}

export async function writeStorage<T>(filename: string, data: T): Promise<void> {
  await mkdir(DATA_DIR, { recursive: true })
  await writeFile(
    join(DATA_DIR, filename),
    JSON.stringify(data, null, 2),
    'utf-8',
  )
}
