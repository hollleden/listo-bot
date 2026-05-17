'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { Sidebar } from '@/components/listo/sidebar'
import { SearchHeader } from '@/components/listo/search-header'
import { MasonryGrid } from '@/components/listo/pin-card'
import { PinDetailSheet } from '@/components/listo/pin-detail-sheet'
import { LoginScreen } from '@/components/listo/login-screen'
import { type Pin, type FolderType } from '@/lib/listo-data'
import { fetchEntries, updateEntry, deleteEntry } from '@/lib/entries'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

export default function ListoApp() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [selectedFolder, setSelectedFolder] = useState<FolderType>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPin, setSelectedPin] = useState<Pin | null>(null)
  const [pins, setPins] = useState<Pin[]>([])
  const [isResurfaceMode, setIsResurfaceMode] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadPins = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const data = await fetchEntries()
      setPins(data)
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : 'Failed to load memories from Supabase'
      )
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isLoggedIn) {
      loadPins()
    }
  }, [isLoggedIn, loadPins])

  // Handle dark mode
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  // Handle sidebar collapse on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsSidebarCollapsed(true)
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const availableFolders = useMemo(() => {
    const uniqueFolders = [...new Set(pins.map((pin) => pin.folder))].sort()
    return ['all', ...uniqueFolders] as FolderType[]
  }, [pins])

  useEffect(() => {
    if (selectedFolder !== 'all' && !availableFolders.includes(selectedFolder)) {
      setSelectedFolder('all')
    }
  }, [availableFolders, selectedFolder])

  // Filter pins based on search and folder
  const filteredPins = useMemo(() => {
    return pins.filter((pin) => {
      const matchesFolder = selectedFolder === 'all' || pin.folder === selectedFolder
      const query = searchQuery.toLowerCase().trim()
      if (!query) return matchesFolder

      const matchesSearch =
        pin.title.toLowerCase().includes(query) ||
        pin.summary.toLowerCase().includes(query) ||
        pin.source.toLowerCase().includes(query) ||
        pin.folder.toLowerCase().includes(query) ||
        (pin.transcription?.toLowerCase().includes(query) ?? false) ||
        pin.tags.some((t) => t.toLowerCase().includes(query))

      return matchesFolder && matchesSearch
    })
  }, [pins, selectedFolder, searchQuery])

  // Handle pin save
  const handleSavePin = async (updatedPin: Pin) => {
    setIsSaving(true)
    const previousPins = pins

    setPins(pins.map((p) => (p.id === updatedPin.id ? updatedPin : p)))
    setSelectedPin(updatedPin)

    try {
      await updateEntry(updatedPin)
    } catch (error) {
      setPins(previousPins)
      setSelectedPin(previousPins.find((p) => p.id === updatedPin.id) ?? null)
      alert(
        error instanceof Error ? error.message : 'Failed to save changes to Supabase'
      )
    } finally {
      setIsSaving(false)
    }
  }

  // Handle pin delete
  const handleDeletePin = async (pinId: number) => {
    setIsSaving(true)
    const previousPins = pins

    setPins(pins.filter((p) => p.id !== pinId))
    setSelectedPin(null)

    try {
      await deleteEntry(pinId)
    } catch (error) {
      setPins(previousPins)
      alert(
        error instanceof Error ? error.message : 'Failed to delete entry from Supabase'
      )
    } finally {
      setIsSaving(false)
    }
  }

  // Handle resurface - randomly selects an older/forgotten memory
  const handleResurface = () => {
    const pool = filteredPins.length > 0 ? filteredPins : pins

    if (isResurfaceMode) {
      setIsResurfaceMode(false)
      setSelectedPin(null)
    } else if (pool.length > 0) {
      const randomIndex = Math.floor(Math.random() * pool.length)
      setIsResurfaceMode(true)
      setSelectedPin(pool[randomIndex])
    }
  }

  if (!isLoggedIn) {
    return <LoginScreen onLogin={() => setIsLoggedIn(true)} />
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        isDarkMode={isDarkMode}
        onToggleDarkMode={() => setIsDarkMode(!isDarkMode)}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        onResurface={handleResurface}
        isResurfaceActive={isResurfaceMode}
      />

      {/* Main Content */}
      <main
        className={cn(
          'min-h-screen flex flex-col transition-all duration-300',
          isSidebarCollapsed ? 'ml-[52px]' : 'ml-[180px]'
        )}
      >
        {/* Search Header */}
        <SearchHeader
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedFolder={selectedFolder}
          onFolderChange={setSelectedFolder}
          totalPins={pins.length}
          filteredPins={filteredPins.length}
          folders={availableFolders}
        />

        {/* Content Grid */}
        <section className="flex-1 p-4">
          {loadError && (
            <div className="mb-4 border border-destructive/40 bg-destructive/10 px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-destructive flex items-center justify-between gap-4">
              <span>{loadError}</span>
              <button
                type="button"
                onClick={loadPins}
                className="underline hover:no-underline shrink-0"
              >
                Retry
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="py-24 flex flex-col items-center justify-center gap-3">
              <Spinner className="size-6 text-muted-foreground" />
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                Syncing memories...
              </p>
            </div>
          ) : (
            <MasonryGrid pins={filteredPins} onPinClick={setSelectedPin} />
          )}
        </section>
      </main>

      {/* Pin Detail Sheet */}
      <PinDetailSheet
        pin={selectedPin}
        isOpen={selectedPin !== null}
        onClose={() => {
          setSelectedPin(null)
          if (isResurfaceMode) {
            setIsResurfaceMode(false)
          }
        }}
        onSave={handleSavePin}
        onDelete={handleDeletePin}
        isSaving={isSaving}
      />
    </div>
  )
}
