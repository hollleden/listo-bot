export interface Pin {
  id: number
  emoji: string
  title: string
  summary: string
  folder: string
  date: string
  tags: string[]
  source: string
  isPublic: boolean
  transcription?: string
  extractedLinks?: string[]
}

export type FolderType = 'all' | string

export const FOLDER_COLORS: Record<FolderType, string> = {
  all: 'bg-muted',
  Crecer: 'bg-folder-crecer',
  Salud: 'bg-folder-salud',
  Creatividad: 'bg-folder-creatividad',
  Descanso: 'bg-folder-descanso',
  Dinero: 'bg-folder-dinero',
  Trabajo: 'bg-folder-trabajo',
  Personal: 'bg-folder-personal',
}

export const INITIAL_PINS: Pin[] = [
  { 
    id: 1, 
    emoji: '01', 
    title: 'AI Assistant Architecture', 
    summary: 'Implement manual editing of connections and tags by users, preventing neural network hallucinations in logic chains. Consider graph-based visualization for relationship mapping.', 
    folder: 'Creatividad', 
    date: '2026-05-17', 
    tags: ['AI', 'UX', 'LISTO', 'ARCHITECTURE'], 
    source: 'TG_BOT',
    isPublic: true,
    transcription: 'Voice memo captured during morning commute. Key points about implementing manual override systems for AI-generated connections. Need to research graph databases for efficient relationship storage.',
    extractedLinks: ['https://neo4j.com/docs', 'https://arxiv.org/ai-hallucination-2026']
  },
  { 
    id: 2, 
    emoji: '02', 
    title: 'Football Training Metrics', 
    summary: 'Post-match activity analysis from Oura. Peak cardio performance, recovery time estimation, and impact on deep sleep phase detected.', 
    folder: 'Salud', 
    date: '2026-05-15', 
    tags: ['OURA', 'FOOTBALL', 'HEALTH', 'BIOMETRICS'], 
    source: 'OURA_SYNC',
    isPublic: false,
    transcription: 'Automatic sync from Oura Ring API. Heart rate variability showed significant improvement post-match. Deep sleep increased by 23%.',
    extractedLinks: ['https://ouraring.com/activity/2026-05-15']
  },
  { 
    id: 3, 
    emoji: '03', 
    title: 'Primavera Sound 2026 Lineup', 
    summary: 'Stage schedules and artist roster for June festival. Need to create timeline to catch all key sets. Priority: LCD Soundsystem, Jungle, Parcels.', 
    folder: 'Descanso', 
    date: '2026-05-12', 
    tags: ['FESTIVAL', 'MUSIC', 'BARCELONA', 'SCHEDULE'], 
    source: 'LINK',
    isPublic: true,
    transcription: 'Scraped from official Primavera Sound website. Main stage conflicts between LCD Soundsystem and Parcels on Saturday.',
    extractedLinks: ['https://primaverasound.com/lineup/2026', 'https://songkick.com/lcd-soundsystem']
  },
  { 
    id: 4, 
    emoji: '04', 
    title: 'PM Onboarding Plan (30-60-90)', 
    summary: 'SMART framework goals defined. Week 1: deep dive into project context and n8n/Mistral AI architecture. Week 2-4: shadow current PMs.', 
    folder: 'Trabajo', 
    date: '2026-05-10', 
    tags: ['MANAGEMENT', 'SMART', 'CAREER', 'ONBOARDING'], 
    source: 'NOTION',
    isPublic: false,
    transcription: 'Exported from Notion workspace. Contains detailed breakdown of first 90 days milestones and key stakeholder meetings.',
    extractedLinks: ['https://notion.so/pm-onboarding-2026']
  },
  { 
    id: 5, 
    emoji: '05', 
    title: 'Subscription Optimization', 
    summary: 'Audit active tokens and limits in Supabase and Mistral API. Migrate unused databases to free tiers. Potential savings: €47/month.', 
    folder: 'Dinero', 
    date: '2026-05-08', 
    tags: ['FINANCE', 'BOOTSTRAP', 'SAAS', 'OPTIMIZATION'], 
    source: 'SUPABASE',
    isPublic: false,
    transcription: 'Monthly cost analysis from Supabase dashboard export. Three unused projects identified for migration.',
    extractedLinks: ['https://supabase.com/dashboard/projects']
  },
  { 
    id: 6, 
    emoji: '06', 
    title: 'Korean Skincare INCI Analysis', 
    summary: 'Active ingredient breakdown (collagen, peptides, niacinamide) for Medicube and Anua brands. Based on official lab data and clinical studies.', 
    folder: 'Crecer', 
    date: '2026-05-01', 
    tags: ['SKINCARE', 'HEALTH', 'RESEARCH', 'INCI'], 
    source: 'MANUAL',
    isPublic: true,
    transcription: 'Research compilation from INCIdecoder and clinical papers. Key finding: 5% niacinamide concentration optimal for oil control.',
    extractedLinks: ['https://incidecoder.com/medicube', 'https://pubmed.ncbi.nlm.nih.gov/skincare-2026']
  },
  { 
    id: 7, 
    emoji: '07', 
    title: 'Morning Routine Optimization', 
    summary: 'Testing new 5am routine: meditation, cold exposure, journaling. Track energy levels and productivity correlation over 30 days.', 
    folder: 'Personal', 
    date: '2026-04-28', 
    tags: ['HABITS', 'WELLNESS', 'EXPERIMENT', 'ROUTINE'], 
    source: 'MANUAL',
    isPublic: false,
    transcription: 'Personal experiment log. Day 1-7 showed 15% improvement in morning focus scores. Cold shower duration: 2 minutes.',
    extractedLinks: ['https://hubermanlab.com/cold-exposure']
  },
  { 
    id: 8, 
    emoji: '08', 
    title: 'n8n Workflow Templates', 
    summary: 'Collection of reusable automation workflows: RSS to Notion, Telegram to Supabase, Calendar sync patterns. Document and share on GitHub.', 
    folder: 'Trabajo', 
    date: '2026-04-25', 
    tags: ['AUTOMATION', 'N8N', 'TEMPLATES', 'GITHUB'], 
    source: 'NOTION',
    isPublic: true,
    transcription: 'Workflow documentation exported from n8n instance. Contains 12 production-ready templates with error handling.',
    extractedLinks: ['https://github.com/user/n8n-templates', 'https://n8n.io/workflows']
  },
]

export const FOLDERS: FolderType[] = ['all', 'Crecer', 'Salud', 'Creatividad', 'Descanso', 'Dinero', 'Trabajo', 'Personal']
