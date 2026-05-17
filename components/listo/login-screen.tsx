'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface LoginScreenProps {
  onLogin: () => void
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async () => {
    if (token.trim().length < 6) {
      setError('INVALID_ACCESS_TOKEN')
      return
    }

    setIsLoading(true)
    // Simulate auth delay
    await new Promise(resolve => setTimeout(resolve, 500))
    setIsLoading(false)
    setError('')
    onLogin()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleLogin()
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        {/* Card */}
        <div className="bg-card border border-border">
          {/* Technical header */}
          <div className="border-b border-border px-4 py-2 bg-secondary/50">
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              TOKEN_GATE // AUTH_VERIFICATION
            </span>
          </div>

          <div className="p-6">
            {/* Logo */}
            <div className="flex flex-col items-center mb-8">
              <div className="w-16 h-16 border border-border bg-foreground text-background flex items-center justify-center font-mono text-2xl font-bold mb-4">
                L
              </div>
              <h1 className="text-xl font-semibold text-foreground">LISTO</h1>
              <p className="font-mono text-[10px] text-muted-foreground mt-1 uppercase tracking-wider">
                SECOND_BRAIN_INTERFACE
              </p>
            </div>

            {/* Form */}
            <div className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="token" className="font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                  ACCESS_TOKEN
                </label>
                <Input
                  id="token"
                  type="password"
                  value={token}
                  onChange={(e) => {
                    setToken(e.target.value)
                    setError('')
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="PASTE_TOKEN_HERE"
                  className={cn(
                    'h-11 font-mono text-xs uppercase tracking-wider bg-card border-border',
                    error && 'border-destructive'
                  )}
                />
                {error && (
                  <p className="font-mono text-[10px] text-destructive uppercase tracking-wider">{error}</p>
                )}
              </div>

              <Button 
                onClick={handleLogin} 
                className="w-full h-11 font-mono text-xs uppercase tracking-wider"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                    AUTHENTICATING...
                  </span>
                ) : (
                  'VERIFY_ACCESS'
                )}
              </Button>
            </div>

            {/* Footer */}
            <p className="font-mono text-[10px] text-center text-muted-foreground mt-6 uppercase tracking-wider">
              GET_TOKEN_FROM{' '}
              <a href="#" className="text-foreground hover:underline">@LISTO_BRAIN_BOT</a>
            </p>
          </div>
        </div>

        {/* Bottom text */}
        <p className="font-mono text-[9px] text-center text-muted-foreground mt-6 uppercase tracking-wider">
          AI_POWERED_KNOWLEDGE_MANAGEMENT // V1.2
        </p>
      </div>
    </div>
  )
}
