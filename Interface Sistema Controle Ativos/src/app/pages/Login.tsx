import React, { useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Lock, User, KeyRound, UserPlus } from 'lucide-react'
import opusLogo from "figma:asset/c9f2c714a5ddd14a6467e06cf02cb98c7a5ac343.png"

export function Login() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      navigate('/dashboard')
    }, 1000)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#050507] text-white relative overflow-hidden">
      {/* Dynamic Background Texture */}
      <div className="absolute inset-0 tech-grid opacity-30" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-wine-main/10 rounded-full blur-[120px] pointer-events-none" />

      <Card className="w-full max-w-md z-10 border-white/5 bg-black/60 backdrop-blur-xl shadow-2xl overflow-hidden relative group">
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-wine-glow to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-700" />
        
        <CardHeader className="space-y-4 pt-10 text-center flex flex-col items-center border-none">
          <div className="bg-white p-3 rounded-lg shadow-[0_0_20px_rgba(255,255,255,0.15)] mb-2">
             <img src={opusLogo} alt="Opus Medical" className="h-12 w-auto object-contain brightness-95" />
          </div>
          <CardTitle className="text-xl font-medium tracking-wide text-white/90">
            SYSTEM <span className="text-wine-glow font-bold">ACCESS</span>
          </CardTitle>
          <p className="text-sm text-muted-foreground">Autenticação de uso restrito corporativo</p>
        </CardHeader>
        
        <CardContent className="px-10 pb-10">
          <form onSubmit={handleLogin} className="space-y-5 mt-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Credencial</label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <User className="h-4 w-4" />
                </div>
                <Input 
                  type="text" 
                  placeholder="ID do Usuário" 
                  className="pl-10 h-11 bg-white/5 border-white/10 text-white placeholder:text-muted-foreground/50 focus:border-wine-glow/50 focus:bg-white/10 transition-all"
                  required
                  defaultValue="admin"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Chave de Acesso</label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <Lock className="h-4 w-4" />
                </div>
                <Input 
                  type="password" 
                  placeholder="••••••••" 
                  className="pl-10 h-11 bg-white/5 border-white/10 text-white placeholder:text-muted-foreground/50 focus:border-wine-glow/50 focus:bg-white/10 transition-all"
                  required
                  defaultValue="password"
                />
              </div>
            </div>

            <div className="flex items-center justify-between mt-4">
              <label className="flex items-center space-x-2 text-xs text-muted-foreground cursor-pointer group">
                <div className="relative flex items-center justify-center w-4 h-4 border border-white/20 rounded bg-white/5 group-hover:border-wine-glow transition-colors">
                  <input type="checkbox" className="peer absolute opacity-0 w-full h-full cursor-pointer" />
                  <div className="hidden peer-checked:block w-2 h-2 bg-wine-glow rounded-sm" />
                </div>
                <span>Lembre-se de mim</span>
              </label>
              
              <a href="#" className="flex items-center text-xs text-wine-glow hover:text-wine-main transition-colors font-medium">
                <KeyRound className="w-3 h-3 mr-1.5" />
                Esqueci a senha
              </a>
            </div>

            <Button 
              type="submit" 
              variant="wine" 
              className="w-full h-11 text-[13px] uppercase tracking-[0.2em] font-bold mt-4"
              disabled={loading}
            >
              {loading ? (
                <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              ) : (
                "Inicializar Sessão"
              )}
            </Button>
            
            <div className="pt-2">
              <Button 
                type="button" 
                variant="outline" 
                className="w-full h-10 text-xs font-medium text-muted-foreground hover:text-white border-white/5 hover:border-white/10"
              >
                <UserPlus className="w-3.5 h-3.5 mr-2 text-white/50" />
                Solicitar novo acesso corporativo
              </Button>
            </div>
          </form>
          
          <div className="mt-6 text-center border-t border-white/5 pt-5">
             <p className="text-[10px] uppercase tracking-wider text-muted-foreground/50">
               Conexão Segura Estabelecida • Opus Medical 2026
             </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
