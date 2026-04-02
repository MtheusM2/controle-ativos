import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Activity, HardDrive, AlertTriangle, MonitorPlay, PlusSquare } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

const data = [
  { name: 'Jan', value: 4000 },
  { name: 'Fev', value: 3000 },
  { name: 'Mar', value: 2000 },
  { name: 'Abr', value: 2780 },
  { name: 'Mai', value: 1890 },
  { name: 'Jun', value: 2390 },
  { name: 'Jul', value: 3490 },
];

export function Dashboard() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700 relative">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* Card 1 */}
        <Card className="bg-black/40 border-white/5 backdrop-blur-sm overflow-hidden relative group">
          <div className="absolute right-0 top-0 w-32 h-32 bg-wine-glow/10 rounded-bl-full blur-[40px] pointer-events-none group-hover:bg-wine-glow/20 transition-all duration-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none pt-6">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Total de Ativos
            </CardTitle>
            <div className="h-8 w-8 rounded bg-white/5 flex items-center justify-center border border-white/10 text-white/80">
              <HardDrive className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-white/90">2.543</div>
            <p className="text-xs text-emerald-400 mt-2 flex items-center">
              +4% em relação ao mês anterior
            </p>
          </CardContent>
        </Card>

        {/* Card 2 */}
        <Card className="bg-black/40 border-white/5 backdrop-blur-sm overflow-hidden relative group">
          <div className="absolute right-0 top-0 w-32 h-32 bg-wine-glow/10 rounded-bl-full blur-[40px] pointer-events-none group-hover:bg-wine-glow/20 transition-all duration-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none pt-6">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Equipamentos Ativos
            </CardTitle>
            <div className="h-8 w-8 rounded bg-white/5 flex items-center justify-center border border-white/10 text-white/80">
               <Activity className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-white/90">2.190</div>
            <p className="text-xs text-muted-foreground mt-2">
              Operando em capacidade normal
            </p>
          </CardContent>
        </Card>

        {/* Card 3 */}
        <Card className="bg-black/40 border-white/5 backdrop-blur-sm overflow-hidden relative group">
          <div className="absolute right-0 top-0 w-32 h-32 bg-amber-500/10 rounded-bl-full blur-[40px] pointer-events-none group-hover:bg-amber-500/20 transition-all duration-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none pt-6">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Em Manutenção
            </CardTitle>
            <div className="h-8 w-8 rounded bg-amber-500/10 flex items-center justify-center border border-amber-500/20 text-amber-500">
               <MonitorPlay className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-white/90">142</div>
            <p className="text-xs text-amber-500 mt-2">
              Aguardando peças: 34
            </p>
          </CardContent>
        </Card>

        {/* Card 4 */}
        <Card className="bg-black/40 border-white/5 backdrop-blur-sm overflow-hidden relative group border-l-2 border-l-destructive/50">
          <div className="absolute right-0 top-0 w-32 h-32 bg-destructive/10 rounded-bl-full blur-[40px] pointer-events-none group-hover:bg-destructive/20 transition-all duration-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none pt-6">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Alertas Críticos
            </CardTitle>
            <div className="h-8 w-8 rounded bg-destructive/10 flex items-center justify-center border border-destructive/20 text-destructive">
               <AlertTriangle className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-destructive">12</div>
            <p className="text-xs text-muted-foreground mt-2">
              Garantia vencendo em 30 dias
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-7 mt-8">
        <Card className="col-span-4 bg-black/40 border-white/5 backdrop-blur-sm">
          <CardHeader className="border-b border-white/5 pb-4">
            <CardTitle className="text-sm uppercase tracking-wider text-white/80">Fluxo de Aquisições</CardTitle>
          </CardHeader>
          <CardContent className="pt-6 pl-2 h-[300px]">
             <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#b3001b" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#b3001b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.2)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="rgba(255,255,255,0.2)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `R$${value/1000}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#121215', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#e0e0e5' }}
                />
                <Area type="monotone" dataKey="value" stroke="#b3001b" strokeWidth={2} fillOpacity={1} fill="url(#colorValue)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="col-span-3 bg-black/40 border-white/5 backdrop-blur-sm">
          <CardHeader className="border-b border-white/5 pb-4">
            <CardTitle className="text-sm uppercase tracking-wider text-white/80">Atividades Recentes</CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
             {[
               { icon: Activity, text: "Monitor Multiparamétrico", action: "calibrado", date: "Há 2 horas", color: "text-emerald-400" },
               { icon: AlertTriangle, text: "Bomba de Infusão", action: "alerta manutenção", date: "Há 4 horas", color: "text-amber-500" },
               { icon: PlusSquare, text: "Ventilador Pulmonar", action: "registrado", date: "Ontem, 14:30", color: "text-white/80" },
               { icon: HardDrive, text: "Desfibrilador", action: "transferido", date: "Ontem, 09:15", color: "text-white/80" }
             ].map((item, i) => (
               <div key={i} className="flex items-start gap-4 group">
                 <div className={`mt-0.5 h-8 w-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 ${item.color} group-hover:bg-white/10 transition-colors`}>
                   <item.icon className="h-4 w-4" />
                 </div>
                 <div className="flex-1 space-y-1">
                   <p className="text-sm font-medium leading-none text-white/90">
                     {item.text}
                   </p>
                   <p className="text-xs text-muted-foreground">
                     Foi {item.action} • {item.date}
                   </p>
                 </div>
               </div>
             ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
