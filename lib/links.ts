import { assertSupabaseConfigured, supabase } from '@/lib/supabase'
import type { Pin } from '@/lib/listo-data'

/** Row shape from public.links (compatible with legacy entries columns). */
export interface DbLink {
  id: number | string
  user_id?: number | null
  created_at?: string | null
  media_type?: string | null
  raw_content?: string | null
  summary?: string | null
  description?: string | null
  tags?: string | string[] | null
  folder?: string | null
  enrichment?: string | null
  title?: string | null
  url?: string | null
  link?: string | null
  source?: string | null
  is_public?: boolean | null
  fact_check?: string | null
  formatted_output?: string | null
  content_type?: string | null
  message_id?: number | null
}

function parseTags(tags: string | string[] | null | undefined): string[] {
  if (!tags) return []

  if (Array.isArray(tags)) {
    return tags.map((tag) => String(tag).replace(/^#/, '').trim().toUpperCase()).filter(Boolean)
  }

  const trimmed = tags.trim()
  if (trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed) as unknown
      if (Array.isArray(parsed)) {
        return parsed
          .map((tag) => String(tag).replace(/^#/, '').trim().toUpperCase())
          .filter(Boolean)
      }
    } catch {
      // fall through to hashtag parsing
    }
  }

  return trimmed
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

function parseEnrichmentLinks(enrichment: string | null | undefined): string[] {
  if (!enrichment) return []

  try {
    const parsed = JSON.parse(enrichment) as {
      websites?: Array<{ url?: string }>
      books?: Array<{ title?: string; author?: string }>
    }

    const urls: string[] = []

    parsed.websites?.forEach((site) => {
      if (site.url) urls.push(site.url)
    })

    parsed.books?.forEach((book) => {
      if (book.title) {
        const query = encodeURIComponent(
          [book.title, book.author].filter(Boolean).join(' ')
        )
        urls.push(`https://www.google.com/search?q=${query}`)
      }
    })

    return [...new Set(urls)]
  } catch {
    return []
  }
}

function mapMediaTypeToSource(mediaType: string | null | undefined, source: string | null | undefined): string {
  if (source) return source.toUpperCase()

  if (!mediaType) return 'MANUAL'

  const normalized = mediaType.toUpperCase()
  if (normalized === 'IMAGE_GROUP' || normalized === 'VIDEO' || normalized === 'IMAGE') {
    return 'TG_BOT'
  }
  if (normalized === 'TEXT') return 'MANUAL'
  return normalized
}

function formatDate(createdAt: string | null | undefined): string {
  if (!createdAt) return new Date().toISOString().slice(0, 10)
  return createdAt.slice(0, 10)
}

function titleFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return 'Untitled link'
  }
}

function numericId(id: number | string): number {
  if (typeof id === 'number') return id
  const parsed = Number.parseInt(id, 10)
  return Number.isFinite(parsed) ? parsed : 0
}

export function linkToPin(row: DbLink): Pin {
  const id = numericId(row.id)
  const primaryUrl = row.url ?? row.link
  const extractedFromEnrichment = parseEnrichmentLinks(row.enrichment)
  const extractedLinks = primaryUrl
    ? [primaryUrl, ...extractedFromEnrichment.filter((url) => url !== primaryUrl)]
    : extractedFromEnrichment

  return {
    id,
    emoji: String(id).padStart(2, '0'),
    title: row.title ?? (primaryUrl ? titleFromUrl(primaryUrl) : 'Untitled link'),
    summary: row.summary ?? row.description ?? '',
    folder: row.folder ?? 'Personal',
    date: formatDate(row.created_at),
    tags: parseTags(row.tags),
    source: mapMediaTypeToSource(row.media_type, row.source),
    isPublic: row.is_public ?? false,
    transcription: row.raw_content ?? undefined,
    extractedLinks: extractedLinks.length > 0 ? extractedLinks : undefined,
  }
}

export async function fetchLinks(): Promise<Pin[]> {
  assertSupabaseConfigured()

  let { data, error } = await supabase
    .from('links')
    .select('*')
    .order('created_at', { ascending: false })

  // Support projects that still expose the legacy `entries` table name.
  if (error?.code === 'PGRST205') {
    const fallback = await supabase
      .from('entries')
      .select('*')
      .order('created_at', { ascending: false })
    data = fallback.data
    error = fallback.error
  }

  if (error) throw error
  return (data as DbLink[]).map(linkToPin)
}

export async function updateLink(pin: Pin): Promise<void> {
  assertSupabaseConfigured()

  const payload = {
    folder: pin.folder,
    tags: serializeTags(pin.tags),
  }

  let { error } = await supabase.from('links').update(payload).eq('id', pin.id)
  if (error?.code === 'PGRST205') {
    const fallback = await supabase.from('entries').update(payload).eq('id', pin.id)
    error = fallback.error
  }
  if (error) throw error
}

export async function deleteLink(pinId: number): Promise<void> {
  assertSupabaseConfigured()

  let { error } = await supabase.from('links').delete().eq('id', pinId)
  if (error?.code === 'PGRST205') {
    const fallback = await supabase.from('entries').delete().eq('id', pinId)
    error = fallback.error
  }
  if (error) throw error
}
