'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
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
  Globe,
  Lock,
  ChevronDown,
  ChevronUp,
  X,
  ArrowLeft,
  Share2,
  Copy,
  Check
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Pin, FolderType } from '@/lib/listo-data'
import { FOLDER_ICONS, FOLDERS } from '@/lib/listo-data'

interface PinDetailViewProps {
  pin: Pin
  onClose: () => void
  onSave: (pin: Pin) => void
  onDelete: (pinId: number) => void
  relatedPins: Pin[]
  onPinClick: (pin: Pin) => void
}

// Generate soft gradient backgrounds based on folder
function getFolderGradient(folder: string): string {
  const gradients: Record<string, string> = {
    Crecer: 'from-emerald-50 to-teal-50',
    Salud: 'from-rose-50 to-pink-50',
    Creatividad: 'from-amber-50 to-yellow-50',
    Descanso: 'from-sky-50 to-blue-50',
    Dinero: 'from-violet-50 to-purple-50',
    Trabajo: 'from-orange-50 to-amber-50',
    Personal: 'from-pink-50 to-rose-50',
  }
  return gradients[folder] || 'from-gray-50 to-slate-50'
}

export function PinDetailView({ pin, onClose, onSave, onDelete, relatedPins, onPinClick }: PinDetailViewProps) {
  const [editedPin, setEditedPin] = useState<Pin>(pin)
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [newTag, setNewTag] = useState('')

  // Sync when pin changes
  useEffect(() => {
    setEditedPin(pin)
  }, [pin])

  const handleDelete = () => {
    if (confirm('Delete this memory? This cannot be undone.')) {
      onDelete(editedPin.id)
      onClose()
    }
  }

  const handleAddTag = () => {
    if (newTag.trim()) {
      setEditedPin({
        ...editedPin,
        tags: [...editedPin.tags, newTag.trim()]
      })
      setNewTag('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedPin({
      ...editedPin,
      tags: editedPin.tags.filter(tag => tag !== tagToRemove)
    })
  }

  const handleShare = async () => {
    const url = `${window.location.origin}?id=${editedPin.id}`
    await navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleToggleVisibility = () => {
    const updated = { ...editedPin, isPublic: !editedPin.isPublic }
    setEditedPin(updated)
    onSave(updated)
  }

  const cleanTranscription = (text?: string) => {
    if (!text) return 'No transcription available.'
    return text.replace(/<[^>]*>/g, '')
  }

  const folderIcon = FOLDER_ICONS[editedPin.folder as FolderType] || ''

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="sticky top-0 bg-background/95 backdrop-blur-sm z-50 border-b border-border/50">
        <div className="flex items-center justify-between px-4 py-3 max-w-7xl mx-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="gap-2 -ml-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleShare}
              className="rounded-full"
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Share2 className="w-4 h-4" />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleDelete}
              className="rounded-full text-destructive hover:text-destructive"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
            <a
              href="https://t.me/listo_brain_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#2AABEE] text-white rounded-full text-sm font-medium hover:bg-[#229ED9] transition-colors"
            >
              Open in Telegram
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 lg:gap-8 p-4 lg:p-8">
          {/* Left Column - Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Visual Header */}
            <div className={cn(
              'h-48 rounded-2xl bg-gradient-to-br flex items-center justify-center',
              getFolderGradient(editedPin.folder)
            )}>
              <span className="text-7xl">{folderIcon}</span>
            </div>

            {/* Title & Meta */}
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="px-3 py-1 bg-secondary rounded-full text-xs text-muted-foreground">
                  {editedPin.folder}
                </span>
                <span className="text-xs text-muted-foreground">{editedPin.source}</span>
                <span className="text-xs text-muted-foreground">{editedPin.date}</span>
              </div>
              <h1 className="text-2xl font-bold text-foreground mb-4">{editedPin.title}</h1>
            </div>

            {/* Summary Section */}
            <section>
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                Summary
              </h2>
              <div className="bg-secondary/50 rounded-xl p-4">
                <p className="text-[15px] text-foreground leading-relaxed">
                  {editedPin.summary}
                </p>
              </div>
            </section>

            {/* Transcription Section */}
            <section>
              <button 
                onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
                className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2 hover:text-primary transition-colors w-full text-left"
              >
                <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                Transcription
                {isTranscriptExpanded ? (
                  <ChevronUp className="w-4 h-4 ml-auto text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-4 h-4 ml-auto text-muted-foreground" />
                )}
              </button>
              <div 
                className={cn(
                  'bg-secondary/50 rounded-xl p-4 text-sm text-muted-foreground overflow-hidden transition-all duration-300',
                  isTranscriptExpanded ? 'max-h-[500px] overflow-y-auto' : 'max-h-[80px]'
                )}
              >
                {cleanTranscription(editedPin.transcription)}
              </div>
            </section>

            {/* Extracted Links */}
            <section>
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                Extracted Links
              </h2>
              <div className="space-y-2">
                {(editedPin.extractedLinks || []).length > 0 ? (
                  editedPin.extractedLinks?.map((link, index) => (
                    <a
                      key={index}
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between bg-secondary/50 hover:bg-secondary rounded-xl px-4 py-3 text-sm text-muted-foreground hover:text-foreground transition-colors group"
                    >
                      <span className="truncate">{link}</span>
                      <ExternalLink className="w-4 h-4 shrink-0 ml-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                  ))
                ) : (
                  <div className="bg-secondary/50 rounded-xl px-4 py-3 text-sm text-muted-foreground">
                    No links extracted
                  </div>
                )}
              </div>
            </section>

            {/* Tags */}
            <section>
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                Tags
              </h2>
              <div className="bg-secondary/50 rounded-xl p-4">
                <div className="flex flex-wrap gap-2 mb-3">
                  {editedPin.tags.map((tag) => (
                    <span 
                      key={tag} 
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-background rounded-full text-sm text-foreground group"
                    >
                      #{tag}
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
                    onChange={(e) => setNewTag(e.target.value)}
                    placeholder="Add tag..."
                    className="h-9 text-sm bg-background border-0 rounded-full"
                    onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
                  />
                  <Button 
                    size="sm" 
                    onClick={handleAddTag}
                    className="rounded-full px-4"
                  >
                    Add
                  </Button>
                </div>
              </div>
            </section>

            {/* Settings */}
            <section>
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                Settings
              </h2>
              <div className="bg-secondary/50 rounded-xl p-4 space-y-4">
                {/* Visibility Toggle */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {editedPin.isPublic ? (
                      <Globe className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <Lock className="w-4 h-4 text-muted-foreground" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {editedPin.isPublic ? 'Public' : 'Private'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {editedPin.isPublic ? 'Anyone with the link can view' : 'Only you can view'}
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={editedPin.isPublic}
                    onCheckedChange={handleToggleVisibility}
                  />
                </div>

                {/* Board Selection */}
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">Board</p>
                  <Select 
                    value={editedPin.folder} 
                    onValueChange={(value) => {
                      const updated = { ...editedPin, folder: value }
                      setEditedPin(updated)
                      onSave(updated)
                    }}
                  >
                    <SelectTrigger className="w-40 h-9 text-sm bg-background border-0 rounded-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {FOLDERS.filter(f => f !== 'all').map((folder) => (
                        <SelectItem key={folder} value={folder} className="text-sm">
                          {FOLDER_ICONS[folder]} {folder}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </section>
          </div>

          {/* Right Column - Related Pins */}
          <div className="lg:col-span-1 mt-8 lg:mt-0">
            <h2 className="text-sm font-semibold text-foreground mb-4">Related memories</h2>
            <div className="space-y-4">
              {relatedPins.slice(0, 5).map((relatedPin) => (
                <article
                  key={relatedPin.id}
                  onClick={() => onPinClick(relatedPin)}
                  className="bg-card rounded-xl overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
                >
                  <div className={cn(
                    'h-16 bg-gradient-to-br flex items-center justify-center',
                    getFolderGradient(relatedPin.folder)
                  )}>
                    <span className="text-2xl opacity-60">{FOLDER_ICONS[relatedPin.folder as FolderType]}</span>
                  </div>
                  <div className="p-3">
                    <h3 className="text-sm font-medium text-foreground line-clamp-2 mb-1">
                      {relatedPin.title}
                    </h3>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {relatedPin.summary}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
