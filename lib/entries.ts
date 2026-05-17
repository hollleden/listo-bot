import { assertSupabaseConfigured, supabase } from '@/lib/supabase'
import type { Pin } from '@/lib/listo-data'

export interface DbEntry {
  id: number
  user_id: number
  created_at: string
  media_type: string | null
  raw_content: string | null
  summary: string | null
  tags: string | null
  folder: string | null
  fact_check: string | null
  enrichment: string | null
  title: string | null
  formatted_output: string | null
  content_type: string | null
  message_id: number | null
}

function parseTags(tags: string | null): string[] {
  if (!tags) return []

  return tags
    .split(/\s+/)
    .map((tag) => tag.replace(/^#/, '').trim())
    .filter(Boolean)
    .map((tag) => tag.replace(/_/g, ' ').toUpperCase())
}

function serializeTags(tags: string[]): string {
  return tags
    .map((tag) => `#${tag.toLowerCase().replace(/\s+/g, '_')}`)
    .join(' ')
}

function parseEnrichmentLinks(enrichment: string | null): string[] {
  if (!enrichment) return []

  try {
    const parsed = JSON.parse(enrichment) as {
      websites?: Array<{ url?: string }>
      books?: Array<{ title?: string; author?: string }>
    }

    const links: string[] = []

    parsed.websites?.forEach((site) => {
      if (site.url) links.push(site.url)
    })

    parsed.books?.forEach((book) => {
      if (book.title) {
        const query = encodeURIComponent(
          [book.title, book.author].filter(Boolean).join(' ')
        )
        links.push(`https://www.google.com/search?q=${query}`)
      }
    })

    return [...new Set(links)]
  } catch {
    return []
  }
}

function mapMediaTypeToSource(mediaType: string | null): string {
  if (!mediaType) return 'MANUAL'

  const normalized = mediaType.toUpperCase()
  if (normalized === 'IMAGE_GROUP') return 'TG_BOT'
  if (normalized === 'VIDEO') return 'TG_BOT'
  if (normalized === 'IMAGE') return 'TG_BOT'
  if (normalized === 'TEXT') return 'MANUAL'
  return normalized
}

export function entryToPin(entry: DbEntry): Pin {
  return {
    id: entry.id,
    emoji: String(entry.id).padStart(2, '0'),
    title: entry.title ?? 'Untitled entry',
    summary: entry.summary ?? '',
    folder: entry.folder ?? 'Personal',
    date: entry.created_at,
    tags: parseTags(entry.tags),
    source: mapMediaTypeToSource(entry.media_type),
    isPublic: false,
    transcription: entry.raw_content ?? undefined,
    extractedLinks: parseEnrichmentLinks(entry.enrichment),
  }
}

export async function fetchEntries(): Promise<Pin[]> {
  assertSupabaseConfigured()

  const { data, error } = await supabase
    .from('entries')
    .select('*')
    .order('created_at', { ascending: false })

  if (error) throw error
  return (data as DbEntry[]).map(entryToPin)
}

export async function updateEntry(pin: Pin): Promise<void> {
  assertSupabaseConfigured()

  const { error } = await supabase
    .from('entries')
    .update({
      folder: pin.folder,
      tags: serializeTags(pin.tags),
    })
    .eq('id', pin.id)

  if (error) throw error
}

export async function deleteEntry(pinId: number): Promise<void> {
  assertSupabaseConfigured()

  const { error } = await supabase.from('entries').delete().eq('id', pinId)
  if (error) throw error
}
