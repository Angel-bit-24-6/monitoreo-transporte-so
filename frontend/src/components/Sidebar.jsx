import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import UnitsList from './UnitsList'
import ConnectionStatus from './ConnectionStatus'

const Sidebar = ({ sidebarOpen, onClose }) => {
  const { wsConnected } = useApp()
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <>
      {/* Overlay con blur para móvil */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[1400] md:hidden transition-opacity duration-300"
          onClick={onClose}
        />
      )}

      <div 
        className={`sidebar w-[380px] text-white flex flex-col overflow-hidden transition-all duration-700 ease-out md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:relative fixed top-0 left-0 h-full z-[1500]`}
        id="sidebar"
      >
        {/* Fondo con efecto glassmorphism */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-950">
          {/* Grid pattern animado */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute inset-0" style={{
              backgroundImage: `linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)`,
              backgroundSize: '50px 50px',
              animation: 'grid-move 20s linear infinite'
            }}></div>
          </div>
          
          {/* Orbes luminosos flotantes */}
          <div className="absolute top-20 -left-20 w-64 h-64 bg-cyan-500/20 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-40 -right-20 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 left-1/4 w-48 h-48 bg-teal-500/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }}></div>
        </div>

        {/* Borde luminoso lateral */}
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-transparent via-cyan-400 to-transparent opacity-50"></div>

        {/* Contenido */}
        <div className="relative z-10 flex flex-col h-full">
          {/* Header Premium */}
          <div className="sidebar-header p-8 relative overflow-hidden">
            {/* Efecto de brillo dinámico */}
            <div 
              className="absolute inset-0 opacity-20"
              style={{
                background: `radial-gradient(circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(6, 182, 212, 0.3), transparent 50%)`
              }}
            ></div>

            {/* Líneas decorativas superiores */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-50"></div>
            
            <div className="relative z-10">
              {/* Icono y título */}
              <div className="flex items-center gap-4 mb-4">
                <div className="relative">
                  {/* Anillo exterior pulsante */}
                  <div className="absolute inset-0 w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-400/30 to-blue-500/30 animate-ping"></div>
                  
                  {/* Contenedor del icono */}
                  <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/50 transform hover:scale-110 transition-transform duration-300">
                    <span className="text-3xl">🚍</span>
                    
                    {/* Efecto de brillo */}
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-white/20 to-transparent"></div>
                  </div>
                </div>

                <div className="flex-1">
                  <h1 className="text-3xl font-bold mb-1 bg-gradient-to-r from-cyan-300 via-blue-300 to-cyan-300 bg-clip-text text-transparent animate-gradient bg-[length:200%_auto]">
                    Monitor GPS
                  </h1>
                  <div className="flex items-center gap-2">
                    <div className="relative flex items-center gap-2">
                      <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500 shadow-lg shadow-cyan-500/50"></span>
                      </span>
                      <span className="text-xs font-medium text-cyan-300">Sistema Activo</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stats cards */}
              <div className="grid grid-cols-2 gap-3 mt-6">
                <div className="bg-white/5 backdrop-blur-xl rounded-xl p-3 border border-white/10 hover:bg-white/10 transition-all duration-300 hover:scale-105 hover:border-cyan-400/50">
                  <div className="text-xs text-gray-400 mb-1">Tiempo Real</div>
                  <div className="text-xl font-bold text-cyan-400">24/7</div>
                </div>
                <div className="bg-white/5 backdrop-blur-xl rounded-xl p-3 border border-white/10 hover:bg-white/10 transition-all duration-300 hover:scale-105 hover:border-blue-400/50">
                  <div className="text-xs text-gray-400 mb-1">Precisión</div>
                  <div className="text-xl font-bold text-blue-400">HD</div>
                </div>
              </div>
            </div>

            {/* Líneas decorativas inferiores */}
            <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
          </div>

          {/* Connection Status con diseño mejorado */}
          <div className="px-6">
            <ConnectionStatus />
          </div>

          {/* Lista de unidades */}
          <div className="flex-1 overflow-hidden relative">
            {/* Degradado superior */}
            <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-slate-900/80 to-transparent z-10 pointer-events-none"></div>
            
            <UnitsList onSelectUnit={onClose} />
            
            {/* Degradado inferior */}
            <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-slate-900/80 to-transparent pointer-events-none"></div>
          </div>

          {/* Footer decorativo */}
          <div className="p-4 border-t border-white/5 bg-black/20 backdrop-blur-xl">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                Sistema Operativo
              </span>
              <span className="font-mono opacity-50">v2.0.1</span>
            </div>
          </div>
        </div>

        {/* Botón de cierre para móvil */}
        <button
          onClick={onClose}
          className="md:hidden absolute top-6 right-6 z-20 w-10 h-10 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 flex items-center justify-center hover:bg-white/20 transition-all duration-300 hover:scale-110 active:scale-95"
          aria-label="Cerrar sidebar"
        >
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <style>{`
          @keyframes grid-move {
            0% { transform: translateY(0); }
            100% { transform: translateY(50px); }
          }
          
          @keyframes gradient {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
          }
          
          .animate-gradient {
            animation: gradient 3s ease infinite;
          }
        `}</style>
      </div>
    </>
  )
}

export default Sidebar