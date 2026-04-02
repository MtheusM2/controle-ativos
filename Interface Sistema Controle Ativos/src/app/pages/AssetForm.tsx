import React, { useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { UploadCloud, Save, X, FileText, CheckCircle2, AlertCircle } from 'lucide-react'

export function AssetForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const location = useLocation()
  
  const isEditing = Boolean(id) || location.pathname.includes('/edit')
  const [successMsg, setSuccessMsg] = useState(false)
  const [files, setFiles] = useState<string[]>([])

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    // Simulate save
    setSuccessMsg(true)
    setTimeout(() => {
      setSuccessMsg(false)
      navigate('/assets')
    }, 2000)
  }

  const handleFileUpload = () => {
    const newFile = `doc_anexo_${Math.floor(Math.random() * 1000)}.pdf`
    setFiles([...files, newFile])
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight text-white/90 uppercase">
            {isEditing ? `Modificar Registro • ${id || 'AS-8492'}` : 'Novo Ativo'}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Preencha os dados técnicos do equipamento.
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="ghost" className="text-muted-foreground uppercase text-xs tracking-wider" onClick={() => navigate('/assets')}>
             <X className="mr-2 h-4 w-4" /> Cancelar Operação
          </Button>
        </div>
      </div>

      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-4 rounded-md flex items-center animate-in fade-in zoom-in duration-300 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
          <CheckCircle2 className="h-5 w-5 mr-3 flex-shrink-0" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold uppercase tracking-wider">Operação Concluída</h4>
            <p className="text-xs mt-0.5 opacity-90">Os dados foram sincronizados com sucesso na base corporativa.</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        <Card className="bg-black/40 border-white/5 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute left-0 top-0 w-1 h-full bg-wine-main/50 group-hover:bg-wine-glow transition-colors" />
          <CardHeader className="border-b border-white/5 pb-4 bg-white/[0.02]">
            <CardTitle className="text-sm uppercase tracking-wider text-white/80 flex items-center">
              <DatabaseIcon className="mr-2 h-4 w-4 text-wine-glow" /> 
              Especificações Técnicas
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Identificação (Tag)</label>
              <Input placeholder="Ex: AS-9999" defaultValue={isEditing ? 'AS-8492' : ''} className="font-mono bg-white/5" required />
            </div>
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Nome do Equipamento</label>
              <Input placeholder="Ex: Monitor Multiparamétrico" defaultValue={isEditing ? 'Monitor Multiparamétrico' : ''} className="bg-white/5" required />
            </div>
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Categoria Principal</label>
              <select className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wine-glow hover:border-white/20 appearance-none">
                <option value="med" selected>Equipamento Médico</option>
                <option value="ti">Tecnologia da Informação</option>
                <option value="infra">Infraestrutura e Apoio</option>
              </select>
            </div>
            
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Fabricante</label>
              <Input placeholder="Marca de origem" defaultValue={isEditing ? 'Philips' : ''} className="bg-white/5" />
            </div>
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Modelo</label>
              <Input placeholder="Especificação do modelo" defaultValue={isEditing ? 'IntelliVue MX450' : ''} className="bg-white/5" />
            </div>
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Número de Série (S/N)</label>
              <Input placeholder="S/N" defaultValue={isEditing ? 'PH-9821-XX' : ''} className="font-mono text-xs bg-white/5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-white/5 backdrop-blur-sm relative overflow-hidden group">
           <div className="absolute left-0 top-0 w-1 h-full bg-white/10 group-hover:bg-white/20 transition-colors" />
           <CardHeader className="border-b border-white/5 pb-4 bg-white/[0.02]">
            <CardTitle className="text-sm uppercase tracking-wider text-white/80 flex items-center">
              <MapPinIcon className="mr-2 h-4 w-4 text-white/50" />
              Alocação & Status
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Setor de Operação</label>
              <select className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wine-glow hover:border-white/20 appearance-none">
                <option value="uti" selected>UTI Adulto - Leito 04</option>
                <option value="cc">Centro Cirúrgico</option>
                <option value="ps">Pronto Socorro</option>
                <option value="almox">Almoxarifado Geral</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Condição Atual</label>
              <select className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wine-glow hover:border-white/20 appearance-none">
                <option value="active" selected>Operacional (Ativo)</option>
                <option value="maintenance">Em Manutenção / Calibração</option>
                <option value="inactive">Fora de Uso (Inativo)</option>
              </select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Observações Adicionais</label>
              <textarea 
                className="flex min-h-[80px] w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wine-glow hover:border-white/20 placeholder:text-muted-foreground resize-none"
                placeholder="Detalhes sobre estado de conservação, histórico de falhas, etc."
                defaultValue={isEditing ? 'Equipamento em perfeito estado. Última calibração realizada em 10/11/2025.' : ''}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-white/5 backdrop-blur-sm relative overflow-hidden group border-dashed">
           <CardHeader className="border-b border-white/5 pb-4 bg-white/[0.02]">
            <CardTitle className="text-sm uppercase tracking-wider text-white/80 flex items-center">
              <FileText className="mr-2 h-4 w-4 text-white/50" />
              Documentação de Apoio
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="border-2 border-dashed border-white/10 hover:border-wine-glow/50 bg-black/20 rounded-lg p-8 text-center transition-colors cursor-pointer group/upload" onClick={handleFileUpload}>
              <div className="mx-auto w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover/upload:bg-wine-main/20 group-hover/upload:text-wine-glow transition-colors">
                <UploadCloud className="h-6 w-6 text-muted-foreground group-hover/upload:text-wine-glow" />
              </div>
              <p className="text-sm font-medium text-white/80">Clique para enviar anexos ou arraste arquivos aqui.</p>
              <p className="text-xs text-muted-foreground mt-1">Manuais, Notas Fiscais, Certificados de Calibração (PDF, JPG, PNG)</p>
            </div>

            {files.length > 0 && (
              <div className="mt-6 space-y-2">
                <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-3">Arquivos em Processamento</p>
                {files.map((file, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-md bg-white/5 border border-white/10">
                    <div className="flex items-center">
                      <FileText className="h-4 w-4 text-wine-glow mr-3" />
                      <span className="text-sm text-white/90 font-mono">{file}</span>
                    </div>
                    <Button variant="ghost" size="sm" type="button" className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4 pt-4 border-t border-white/5">
          <Button variant="outline" type="button" onClick={() => navigate('/assets')} className="uppercase text-xs tracking-wider h-11 px-6 bg-transparent hover:bg-white/5 border-white/10 text-white/70">
            Descartar
          </Button>
          <Button variant="wine" type="submit" className="uppercase text-xs tracking-widest font-bold h-11 px-8">
            <Save className="mr-2 h-4 w-4" /> 
            {isEditing ? 'Atualizar Base' : 'Salvar Registro'}
          </Button>
        </div>
      </form>
    </div>
  )
}

function DatabaseIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5V19A9 3 0 0 0 21 19V5" />
      <path d="M3 12A9 3 0 0 0 21 12" />
    </svg>
  )
}

function MapPinIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}
