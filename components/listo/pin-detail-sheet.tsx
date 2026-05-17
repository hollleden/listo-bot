'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  ExternalLink, 
  Trash2, 
  Save,
  Globe,
  Lock,
  ChevronDown,
  ChevronUp,
  X,
  Plus
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Pin, FolderType } from '@/lib/listo-data'
import { FOLDER_COLORS, FOLDERS } from '@/lib/listo-data'

interface PinDetailSheetProps {
  pin: Pin | null
  isOpen: boolean
  onClose: () => void
  onSave: (pin: Pin) => void | Promise<void>
  onDelete: (pinId: number) => void | Promise<void>
  isSaving?: boolean
}

export function PinDetailSheet({ pin, isOpen, onClose, onSave, onDelete, isSaving = false }: PinDetailSheetProps) {
  const [editedPin, setEditedPin] = useState<Pin | null>(null)
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false)
  const [newTag, setNewTag] = useState('')

  // Sync edited pin when pin changes
  if (pin && (!editedPin || editedPin.id !== pin.id)) {
    setEditedPin({ ...pin })
  }

  const handleSave = async () => {
    if (editedPin && !isSaving) {
      await onSave(editedPin)
      onClose()
    }
  }

  const handleDelete = async () => {
    if (editedPin && !isSaving && confirm('DELETE THIS MEMORY ENTRY?')) {
      await onDelete(editedPin.id)
      onClose()
    }
  }

  const folderOptions = [
    ...new Set([
      ...FOLDERS.filter((f) => f !== 'all'),
      editedPin?.folder,
    ].filter(Boolean)),
  ] as string[]

  const handleAddTag = () => {
    if (newTag.trim() && editedPin) {
      setEditedPin({
        ...editedPin,
        tags: [...editedPin.tags, newTag.trim().toUpperCase()]
      })
      setNewTag('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    if (editedPin) {
      setEditedPin({
        ...editedPin,
        tags: editedPin.tags.filter(tag => tag !== tagToRemove)
      })
    }
  }

  const handleToggleVisibility = () => {
    if (editedPin) {
      setEditedPin({
        ...editedPin,
        isPublic: !editedPin.isPublic
      })
    }
  }

  if (!editedPin) return null

  const folderColor = FOLDER_COLORS[editedPin.folder as FolderType] || FOLDER_COLORS.all

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-lg p-0 flex flex-col border-l border-border bg-card">
        {/* Technical header */}
        <div className="border-b border-border bg-secondary/50 px-4 py-2">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            REF_SYS // MEMORY_DETAIL // #{editedPin.emoji}
          </span>
        </div>

        <SheetHeader className="px-4 pt-4 pb-2 border-b border-border">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              <span>{editedPin.source}</span>
              <span>•</span>
              <span>{editedPin.date}</span>
            </div>
            <div className="flex items-center gap-2">
              {editedPin.isPublic ? (
                <Globe className="w-3.5 h-3.5 text-muted-foreground" />
              ) : (
                <Lock className="w-3.5 h-3.5 text-muted-foreground" />
              )}
              <Switch
                checked={editedPin.isPublic}
                onCheckedChange={handleToggleVisibility}
              />
            </div>
          </div>
          <SheetTitle className="text-lg font-semibold leading-snug text-left">
            {editedPin.title}
          </SheetTitle>
          <SheetDescription className="sr-only">
            Memory entry detail view and editor
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1">
          <div className="p-4 space-y-6">
            {/* Section 1: Summary */}
            <section>
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-foreground" />
                SUMMARY
              </div>
              <div className="bg-secondary/50 border border-border p-3">
                <p className="text-sm text-foreground leading-relaxed">
                  {editedPin.summary}
                </p>
              </div>
            </section>

            {/* Section 2: Transcription */}
            <section>
              <button 
                onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
                className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-2 hover:text-foreground transition-colors w-full"
              >
                <span className="w-2 h-2 bg-foreground" />
                TRANSCRIPTION
                {isTranscriptExpanded ? (
                  <ChevronUp className="w-3 h-3 ml-auto" />
                ) : (
                  <ChevronDown className="w-3 h-3 ml-auto" />
                )}
              </button>
              <div 
                className={cn(
                  'bg-secondary/50 border border-border p-3 font-mono text-xs text-muted-foreground overflow-hidden transition-all duration-200',
                  isTranscriptExpanded ? 'max-h-[300px] overflow-y-auto' : 'max-h-[72px]'
                )}
              >
                {editedPin.transcription || 'No transcription available for this entry.'}
              </div>
            </section>

            {/* Section 3: Extracted Links */}
            <section>
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-foreground" />
                EXTRACTED_INDICES
              </div>
              <div className="space-y-1.5">
                {(editedPin.extractedLinks || []).length > 0 ? (
                  editedPin.extractedLinks?.map((link, index) => (
                    <a
                      key={index}
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between bg-secondary/50 border border-border px-3 py-2 text-xs font-mono text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors group"
                    >
                      <span className="truncate">{link}</span>
                      <ExternalLink className="w-3 h-3 shrink-0 ml-2 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                  ))
                ) : (
                  <div className="bg-secondary/50 border border-border px-3 py-2 text-xs font-mono text-muted-foreground">
                    NO_LINKS_EXTRACTED
                  </div>
                )}
              </div>
            </section>

            {/* Section 4: Tags (JSON Array) */}
            <section>
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-foreground" />
                TAGS_ARRAY
              </div>
              <div className="bg-secondary/50 border border-border p-3">
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {editedPin.tags.map((tag) => (
                    <span 
                      key={tag} 
                      className="font-mono text-[9px] uppercase tracking-wider px-2 py-1 bg-card border border-border text-foreground flex items-center gap-1.5 group"
                    >
                      {`"${tag}"`}
                      <button 
                        onClick={() => handleRemoveTag(tag)}
                        className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-all"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value.toUpperCase())}
                    placeholder="ADD_TAG"
                    className="h-8 text-xs font-mono uppercase tracking-wider bg-card border-border"
                    onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
                  />
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="h-8 px-2 border-border"
                    onClick={handleAddTag}
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </section>

            {/* Folder Selection */}
            <section>
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-foreground" />
                TARGET_FOLDER
              </div>
              <Select 
                value={editedPin.folder} 
                onValueChange={(value) => setEditedPin({ ...editedPin, folder: value })}
              >
                <SelectTrigger className="w-full font-mono text-xs uppercase tracking-wider bg-card border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {folderOptions.map((folder) => (
                    <SelectItem key={folder} value={folder} className="font-mono text-xs uppercase">
                      {folder}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {/* Folder color indicator */}
              <div className={cn('h-1 w-full mt-2', folderColor)} />
            </section>
          </div>
        </ScrollArea>

        {/* Actions Footer */}
        <div className="p-4 border-t border-border flex gap-2 bg-secondary/50">
          <Button onClick={handleSave} disabled={isSaving} className="flex-1 font-mono text-xs uppercase tracking-wider">
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? 'SAVING...' : 'SAVE_CHANGES'}
          </Button>
          <Button 
            variant="outline" 
            size="icon" 
            onClick={handleDelete}
            disabled={isSaving}
            className="border-border text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
