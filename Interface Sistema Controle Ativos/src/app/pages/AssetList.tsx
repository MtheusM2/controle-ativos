import React from 'react'
import { useNavigate } from 'react-router'
import { Card, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Badge } from '../components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'
import { Filter, Search, Plus, Edit2, Trash2, Download } from 'lucide-react'

const assets = [
  { id: 'AS-8492', name: 'Monitor Multiparamétrico', type: 'Equipamento Médico', status: 'Ativo', model: 'IntelliVue MX450', location: 'UTI Adulto - Leito 04' },
  { id: 'AS-8493', name: 'Bomba de Infusão', type: 'Equipamento Médico', status: 'Manutenção', model: 'Infusomat Space', location: 'Engenharia Clínica' },
  { id: 'AS-8494', name: 'Desfibrilador', type: 'Equipamento de Apoio', status: 'Ativo', model: 'HeartStart XL', location: 'Pronto Socorro' },
  { id: 'AS-8495', name: 'Ventilador Pulmonar', type: 'Equipamento Médico', status: 'Inativo', model: 'Puritan Bennett 980', location: 'Almoxarifado' },
  { id: 'AS-8496', name: 'Eletrocardiógrafo', type: 'Equipamento Médico', status: 'Ativo', model: 'CardioMax', location: 'Enfermaria B' },
]

export function AssetList() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-medium tracking-tight text-white/90 uppercase">Inventário Global</h2>
          <p className="text-sm text-muted-foreground mt-1">Gestão de rastreabilidade de equipamentos.</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" className="border-white/10 text-muted-foreground uppercase text-xs tracking-wider h-10">
             <Download className="mr-2 h-4 w-4" /> Exportar
          </Button>
          <Button variant="wine" className="uppercase text-xs tracking-wider h-10" onClick={() => navigate('/assets/new')}>
             <Plus className="mr-2 h-4 w-4" /> Novo Registro
          </Button>
        </div>
      </div>

      <Card className="bg-black/60 border-white/10 backdrop-blur-md">
        <CardContent className="p-0">
          <div className="p-4 border-b border-white/5 bg-white/5 flex flex-col md:flex-row gap-4 items-center">
            <div className="relative w-full max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Buscar por código, nome ou modelo..." className="pl-9 h-10 w-full" />
            </div>
            <div className="flex gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0 hide-scrollbar">
              <Button variant="outline" className="bg-white/5 border-white/10 text-white hover:bg-white/10 h-10">
                <Filter className="mr-2 h-4 w-4 text-muted-foreground" /> Filtros Avançados
              </Button>
              <select className="h-10 rounded-md border border-white/10 bg-[#121215] px-3 py-2 text-sm text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wine-glow disabled:cursor-not-allowed disabled:opacity-50 appearance-none min-w-[150px]">
                <option value="">Tipo de Ativo</option>
                <option value="med">Médico</option>
                <option value="ti">TI</option>
                <option value="infra">Infraestrutura</option>
              </select>
              <select className="h-10 rounded-md border border-white/10 bg-[#121215] px-3 py-2 text-sm text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wine-glow disabled:cursor-not-allowed disabled:opacity-50 appearance-none min-w-[150px]">
                <option value="">Status</option>
                <option value="ativo">Ativo</option>
                <option value="manutencao">Manutenção</option>
                <option value="inativo">Inativo</option>
              </select>
            </div>
          </div>
          
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-[100px] font-semibold text-white/50 uppercase tracking-wider text-xs">ID Ativo</TableHead>
                <TableHead className="font-semibold text-white/50 uppercase tracking-wider text-xs">Identificação</TableHead>
                <TableHead className="font-semibold text-white/50 uppercase tracking-wider text-xs">Localização</TableHead>
                <TableHead className="font-semibold text-white/50 uppercase tracking-wider text-xs">Status</TableHead>
                <TableHead className="text-right font-semibold text-white/50 uppercase tracking-wider text-xs">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assets.map((asset) => (
                <TableRow key={asset.id} className="group cursor-default">
                  <TableCell className="font-mono text-xs text-muted-foreground">{asset.id}</TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium text-white/90">{asset.name}</span>
                      <span className="text-xs text-muted-foreground mt-0.5">{asset.model} • {asset.type}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-white/80">{asset.location}</TableCell>
                  <TableCell>
                    <Badge variant={
                      asset.status === 'Ativo' ? 'success' :
                      asset.status === 'Manutenção' ? 'warning' : 'destructive'
                    }>
                      {asset.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => navigate(`/assets/edit/${asset.id}`)}>
                        <Edit2 className="h-4 w-4 text-white/70 hover:text-white" />
                        <span className="sr-only">Editar</span>
                      </Button>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:bg-destructive/20 group/btn">
                        <Trash2 className="h-4 w-4 text-white/70 group-hover/btn:text-destructive transition-colors" />
                        <span className="sr-only">Excluir</span>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          <div className="p-4 border-t border-white/5 flex items-center justify-between text-xs text-muted-foreground bg-black/20">
            <span>Mostrando 1-5 de 2.543 registros</span>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" className="h-7 px-2 border-white/10 bg-transparent text-xs opacity-50 cursor-not-allowed">Anterior</Button>
              <Button variant="outline" size="sm" className="h-7 px-2 border-white/10 bg-white/5 text-white text-xs">1</Button>
              <Button variant="outline" size="sm" className="h-7 px-2 border-white/10 bg-transparent text-xs hover:bg-white/5">2</Button>
              <Button variant="outline" size="sm" className="h-7 px-2 border-white/10 bg-transparent text-xs hover:bg-white/5">3</Button>
              <span className="px-2 self-center">...</span>
              <Button variant="outline" size="sm" className="h-7 px-2 border-white/10 bg-transparent text-xs hover:bg-white/5">Próxima</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
