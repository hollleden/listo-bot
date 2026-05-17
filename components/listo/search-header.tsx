'use client'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { FolderType } from '@/lib/listo-data'
import { FOLDERS } from '@/lib/listo-data'

interface SearchHeaderProps {
  searchQuery: string
  onSearchChange: (value: string) => void
  selectedFolder: FolderType
  onFolderChange: (folder: FolderType) => void
  totalPins: number
  filteredPins: number
  folders?: FolderType[]
}

const FOLDER_LABELS: Record<string, string> = {
  all: 'ALL',
  Crecer: 'CRECER',
  Salud: 'SALUD',
  Creatividad: 'CREATIVIDAD',
  Descanso: 'DESCANSO',
  Dinero: 'DINERO',
  Trabajo: 'TRABAJO',
  Personal: 'PERSONAL',
}

function getFolderLabel(folder: FolderType): string {
  return FOLDER_LABELS[folder] ?? folder.toUpperCase()
}

export function SearchHeader({ 
  searchQuery, 
  onSearchChange, 
  selectedFolder, 
  onFolderChange,
  totalPins,
  filteredPins,
  folders = FOLDERS,
}: SearchHeaderProps) {
  return (
    <header className="sticky top-0 bg-background z-30 border-b border-border">
      {/* Search Bar */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="SEARCH MEMORIES, TAGS, CONNECTIONS..."
              className="pl-10 h-10 bg-card border-border font-mono text-xs uppercase tracking-wider placeholder:text-muted-foreground/60"
            />
          </div>
          <div className="hidden sm:flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground border border-border px-3 py-2 bg-card">
            {filteredPins === totalPins 
              ? `${totalPins} ENTRIES` 
              : `${filteredPins}/${totalPins} FILTERED`}
          </div>
        </div>
      </div>

      {/* Folder Tabs - File Divider Style */}
      <div className="flex items-center overflow-x-auto scrollbar-thin">
        {folders.map((folder, index) => (
          <button
            key={folder}
            onClick={() => onFolderChange(folder)}
            className={cn(
              'relative px-4 py-3 font-mono text-[10px] uppercase tracking-wider transition-colors whitespace-nowrap',
              'border-r border-border',
              selectedFolder === folder 
                ? 'bg-card text-foreground font-bold' 
                : 'bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground',
              index === 0 && 'border-l-0'
            )}
          >
            {getFolderLabel(folder)}
            {selectedFolder === folder && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-foreground" />
            )}
          </button>
        ))}
        {/* Filler to extend border */}
        <div className="flex-1 border-b border-border h-full min-h-[44px] bg-secondary/30" />
      </div>
    </header>
  )
}
