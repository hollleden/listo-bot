'use client'

import { Globe, Lock } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Pin, FolderType } from '@/lib/listo-data'
import { FOLDER_COLORS } from '@/lib/listo-data'

interface PinCardProps {
  pin: Pin
  onClick: () => void
}

export function PinCard({ pin, onClick }: PinCardProps) {
  const folderColor = FOLDER_COLORS[pin.folder as FolderType] || FOLDER_COLORS.all

  return (
    <article
      onClick={onClick}
      className={cn(
        'bg-card border border-border rounded-sm overflow-hidden cursor-pointer relative',
        'transition-all duration-150 ease-out',
        'hover:shadow-[4px_4px_0px_0px_rgba(34,34,34,0.15)]',
        'dark:hover:shadow-[4px_4px_0px_0px_rgba(226,232,240,0.1)]'
      )}
    >
      {/* Technical header strip */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border bg-secondary/50">
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          REF_SYS // {pin.folder.toUpperCase()}
        </span>
        <div className="flex items-center gap-2">
          {pin.isPublic ? (
            <Globe className="w-3 h-3 text-muted-foreground" />
          ) : (
            <Lock className="w-3 h-3 text-muted-foreground" />
          )}
        </div>
      </div>
      
      {/* Card content */}
      <div className="p-3">
        {/* ID + Source row */}
        <div className="flex items-center justify-between mb-2">
          <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
            #{pin.emoji} — {pin.source}
          </span>
          <span className="font-mono text-[10px] text-muted-foreground">
            {pin.date}
          </span>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-sm leading-snug text-foreground mb-2 line-clamp-2">
          {pin.title}
        </h3>

        {/* Summary */}
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3 mb-3">
          {pin.summary}
        </p>

        {/* Tags as technical labels */}
        <div className="flex flex-wrap gap-1.5">
          {pin.tags.slice(0, 4).map((tag) => (
            <span 
              key={tag} 
              className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-secondary border border-border text-muted-foreground"
            >
              {tag}
            </span>
          ))}
          {pin.tags.length > 4 && (
            <span className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-secondary border border-border text-muted-foreground">
              +{pin.tags.length - 4}
            </span>
          )}
        </div>
      </div>

      {/* Folder color indicator bar */}
      <div className={cn('h-1 w-full', folderColor)} />
    </article>
  )
}

interface MasonryGridProps {
  pins: Pin[]
  onPinClick: (pin: Pin) => void
}

export function MasonryGrid({ pins, onPinClick }: MasonryGridProps) {
  if (pins.length === 0) {
    return (
      <div className="py-24 text-center flex flex-col items-center justify-center">
        <div className="w-16 h-16 border border-border bg-card flex items-center justify-center font-mono text-xs text-muted-foreground mb-4">
          NULL
        </div>
        <h3 className="font-semibold text-foreground mb-1">NO DATA FOUND</h3>
        <p className="text-xs text-muted-foreground max-w-xs font-mono uppercase tracking-wider">
          Adjust filters or add entries via TG_BOT
        </p>
      </div>
    )
  }

  return (
    <div className="columns-1 md:columns-2 xl:columns-3 gap-4 [column-fill:balance]">
      {pins.map((pin) => (
        <div key={pin.id} className="break-inside-avoid mb-4">
          <PinCard pin={pin} onClick={() => onPinClick(pin)} />
        </div>
      ))}
    </div>
  )
}
