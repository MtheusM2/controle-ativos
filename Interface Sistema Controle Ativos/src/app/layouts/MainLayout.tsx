import React from "react"
import { Outlet, NavLink, useLocation, useNavigate } from "react-router"
import { 
  LayoutDashboard, 
  Package, 
  PlusSquare, 
  LogOut, 
  User, 
  Settings,
  Filter
} from "lucide-react"
import opusLogo from "figma:asset/d036f4389385c0f460a83cbad2ea6dddb8a79618.png"

export function MainLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  const navItems = [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Controle de Ativos", path: "/assets", icon: Package },
    { name: "Cadastrar Ativo", path: "/assets/new", icon: PlusSquare },
  ]

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground selection:bg-wine-main/40">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col border-r border-border bg-[#0b0b0e] z-10 relative shadow-[4px_0_24px_rgba(0,0,0,0.5)]">
        {/* Logo Area */}
        <div className="h-16 flex items-center px-6 border-b border-border bg-black/40 relative">
          <div className="absolute inset-0 bg-gradient-to-r from-wine-main/10 to-transparent pointer-events-none" />
          <div className="bg-white/90 p-1.5 rounded-sm shadow-[0_0_15px_rgba(255,255,255,0.1)]">
             <img src={opusLogo} alt="Opus Medical" className="h-6 w-auto object-contain brightness-90 contrast-125" />
          </div>
          <span className="ml-3 font-semibold text-sm tracking-wider text-white/90">SYSCORP</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto custom-scrollbar">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path) && (item.path !== '/assets' || location.pathname === '/assets')
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  group flex items-center px-3 py-2.5 rounded-md text-sm font-medium transition-all relative
                  ${isActive 
                    ? "text-white bg-wine-main/10" 
                    : "text-muted-foreground hover:bg-white/5 hover:text-white"
                  }
                `}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-3/5 bg-wine-glow rounded-r-md shadow-[0_0_10px_rgba(179,0,27,0.8)]" />
                    )}
                    <item.icon className={`mr-3 h-4 w-4 ${isActive ? 'text-wine-glow' : 'text-muted-foreground group-hover:text-white/80'}`} />
                    {item.name}
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* User / Logout */}
        <div className="p-4 border-t border-border bg-black/20">
          <div className="flex items-center px-3 py-2 mb-2 rounded-md hover:bg-white/5 cursor-pointer transition-colors">
            <div className="h-8 w-8 rounded-full bg-wine-dark flex items-center justify-center border border-wine-main/50 text-wine-glow shadow-[0_0_8px_rgba(138,10,29,0.4)]">
              <User className="h-4 w-4" />
            </div>
            <div className="ml-3 flex-1 overflow-hidden">
              <p className="text-sm font-medium text-white truncate">Admin Opus</p>
              <p className="text-xs text-muted-foreground truncate">admin@opus.med</p>
            </div>
          </div>
          <button 
            onClick={() => navigate('/')}
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
          >
            <LogOut className="mr-3 h-4 w-4" />
            Sair do sistema
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#0a0a0c] relative">
        {/* Subtle background tech texture over the main area */}
        <div className="absolute inset-0 tech-grid opacity-20 pointer-events-none z-0" />
        
        {/* Topbar */}
        <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-[#0a0a0c]/80 backdrop-blur-md z-10 sticky top-0">
          <div className="flex items-center">
            <h1 className="text-lg font-medium text-white/90 tracking-tight">
              {location.pathname === '/dashboard' ? 'Visão Geral' : 
               location.pathname.includes('/new') ? 'Novo Registro' :
               location.pathname.includes('/edit') ? 'Editar Registro' :
               'Controle de Ativos'}
            </h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <button className="p-2 text-muted-foreground hover:text-white transition-colors">
               <Settings className="h-4 w-4" />
            </button>
            <div className="h-4 w-px bg-border" />
            <div className="text-xs text-muted-foreground bg-white/5 px-2 py-1 rounded border border-white/10">
              Ambiente Seguro
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6 z-10 custom-scrollbar">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
