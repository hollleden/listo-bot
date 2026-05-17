'use client'

import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { 
  Grid3X3, 
  Sparkles, 
  Settings,
  Moon,
  Sun,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarProps {
  isDarkMode: boolean
  onToggleDarkMode: () => void
  isCollapsed: boolean
  onToggleCollapse: () => void
  onResurface: () => void
  isResurfaceActive?: boolean
}

export function Sidebar({ isDarkMode, onToggleDarkMode, isCollapsed, onToggleCollapse, onResurface, isResurfaceActive }: SidebarProps) {
  return (
    <nav 
      className={cn(
        'h-screen bg-card flex flex-col fixed left-0 top-0 bottom-0 z-40 border-r border-border transition-all duration-300',
        isCollapsed ? 'w-[52px]' : 'w-[180px]'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 p-3 border-b border-border">
        <div className="w-7 h-7 bg-foreground text-background flex items-center justify-center font-mono text-sm font-bold shrink-0">
          L
        </div>
        {!isCollapsed && (
          <span className="font-mono text-xs uppercase tracking-wider text-foreground">LISTO</span>
        )}
      </div>

      {/* Navigation Items */}
      <div className="flex flex-col flex-1 py-2">
        <NavItem 
          icon={<Grid3X3 className="w-4 h-4" />} 
          label="BROWSE" 
          isActive={!isResurfaceActive}
          isCollapsed={isCollapsed}
        />
        <NavItem 
          icon={<Sparkles className="w-4 h-4" />} 
          label="RESURFACE" 
          isCollapsed={isCollapsed}
          onClick={onResurface}
          isActive={isResurfaceActive}
        />
        
        <div className="flex-1" />
        
        <div className="border-t border-border pt-2">
          <NavItem 
            icon={isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />} 
            label={isDarkMode ? 'LIGHT' : 'DARK'} 
            onClick={onToggleDarkMode}
            isCollapsed={isCollapsed}
          />
          <NavItem 
            icon={<Settings className="w-4 h-4" />} 
            label="SETTINGS" 
            isCollapsed={isCollapsed}
          />
        </div>
      </div>

      {/* Collapse Toggle */}
      <div className="p-2 border-t border-border">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center text-muted-foreground hover:text-foreground hover:bg-secondary h-7"
          onClick={onToggleCollapse}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </Button>
      </div>

      {/* Version */}
      <div className={cn(
        'p-2 border-t border-border font-mono text-[9px] text-muted-foreground uppercase tracking-wider text-center',
        isCollapsed ? 'rotate-180 [writing-mode:vertical-lr]' : ''
      )}>
        {isCollapsed ? 'V1.2' : 'SYS_V1.2'}
      </div>
    </nav>
  )
}

interface NavItemProps {
  icon: React.ReactNode
  label: string
  isActive?: boolean
  isCollapsed: boolean
  onClick?: () => void
}

function NavItem({ icon, label, isActive, isCollapsed, onClick }: NavItemProps) {
  const button = (
    <Button
      variant="ghost"
      size="sm"
      className={cn(
        'w-full transition-colors rounded-none h-9',
        isCollapsed ? 'justify-center px-0' : 'justify-start px-3',
        isActive 
          ? 'bg-secondary text-foreground border-r-2 border-foreground' 
          : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
      )}
      onClick={onClick}
    >
      {icon}
      {!isCollapsed && <span className="ml-2 font-mono text-[10px] uppercase tracking-wider">{label}</span>}
    </Button>
  )

  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{button}</TooltipTrigger>
        <TooltipContent side="right" className="font-mono text-[10px] uppercase tracking-wider">
          {label}
        </TooltipContent>
      </Tooltip>
    )
  }

  return button
}
