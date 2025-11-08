import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'

const WebSocketMonitor = () => {
  const { wsConnected, units, events, ws } = useApp()
  const [isExpanded, setIsExpanded] = useState(false)
  const [ping, setPing] = useState(0)
  const [connectionTime, setConnectionTime] = useState(null)
  const [uptime, setUptime] = useState(0)
  const [messagesCount, setMessagesCount] = useState(0)

  // Simular ping (en producción vendría del WebSocket)
  useEffect(() => {
    if (!wsConnected) {
      setPing(0)
      return
    }

    const interval = setInterval(() => {
      // Simular ping realista entre 10-50ms
      setPing(Math.floor(Math.random() * 40) + 10)
    }, 2000)

    return () => clearInterval(interval)
  }, [wsConnected])

  // Actualizar tiempo de conexión
  useEffect(() => {
    if (wsConnected && !connectionTime) {
      setConnectionTime(Date.now())
    } else if (!wsConnected) {
      setConnectionTime(null)
      setUptime(0)
    }
  }, [wsConnected, connectionTime])

  // Calcular uptime
  useEffect(() => {
    if (!connectionTime) return

    const interval = setInterval(() => {
      setUptime(Math.floor((Date.now() - connectionTime) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [connectionTime])

  // Contar mensajes recibidos
  useEffect(() => {
    if (!ws) return

    const handleMessage = () => {
      setMessagesCount(prev => prev + 1)
    }

    ws.addEventListener('message', handleMessage)
    return () => ws.removeEventListener('message', handleMessage)
  }, [ws])

  const formatUptime = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const getConnectionQuality = () => {
    if (!wsConnected) return { 
      label: 'Desconectado', 
      color: 'red', 
      gradient: 'from-red-500 to-rose-600',
      icon: '🔴'
    }
    if (ping < 15) return { 
      label: 'Excelente', 
      color: 'emerald', 
      gradient: 'from-emerald-400 via-green-500 to-emerald-600',
      icon: '⚡'
    }
    if (ping < 30) return { 
      label: 'Muy Buena', 
      color: 'cyan', 
      gradient: 'from-cyan-400 via-blue-500 to-cyan-600',
      icon: '✨'
    }
    if (ping < 50) return { 
      label: 'Buena', 
      color: 'yellow', 
      gradient: 'from-yellow-400 via-amber-500 to-yellow-600',
      icon: '⭐'
    }
    return { 
      label: 'Regular', 
      color: 'orange', 
      gradient: 'from-orange-400 via-red-500 to-orange-600',
      icon: '⚠️'
    }
  }

  const quality = getConnectionQuality()
  const activeUnits = Object.values(units).filter(u => u.is_connected).length
  const totalUnits = Object.values(units).length

  return (
    <div className="fixed bottom-6 left-6 z-[1000]">
      <div 
        className={`websocket-monitor relative rounded-3xl overflow-hidden transition-all duration-700 ease-out shadow-2xl ${
          isExpanded ? 'w-[420px]' : 'w-[320px]'
        }`}
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 50%, rgba(15, 23, 42, 0.95) 100%)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {/* Efectos de fondo animados */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-20 -left-20 w-64 h-64 bg-gradient-to-br from-cyan-500/20 via-blue-500/20 to-purple-500/20 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-gradient-to-br from-purple-500/20 via-pink-500/20 to-cyan-500/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-gradient-to-r from-cyan-500/5 via-transparent to-purple-500/5 rounded-full blur-3xl"></div>
        </div>

        {/* Borde luminoso superior */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent"></div>
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-400/30 to-transparent blur-sm"></div>

        {/* Contenido */}
        <div className="relative z-10">
          {/* Header compacto */}
          <div 
            className="p-5 cursor-pointer select-none group transition-all duration-300 hover:bg-white/5"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {/* Indicador de estado premium */}
                <div className="relative">
                  {/* Anillo pulsante */}
                  <div className={`absolute inset-0 rounded-full ${
                    wsConnected 
                      ? 'bg-emerald-500/30 animate-ping' 
                      : 'bg-red-500/30'
                  }`} style={{ animationDuration: '2s' }}></div>
                  
                  {/* Glow exterior */}
                  <div className={`absolute inset-0 rounded-full ${
                    wsConnected 
                      ? 'bg-emerald-500/20 blur-md animate-pulse' 
                      : 'bg-red-500/20 blur-md'
                  }`}></div>
                  
                  {/* Indicador principal */}
                  <div className={`relative w-4 h-4 rounded-full ${
                    wsConnected 
                      ? 'bg-gradient-to-br from-emerald-400 to-green-600 shadow-lg shadow-emerald-500/50' 
                      : 'bg-gradient-to-br from-red-400 to-rose-600 shadow-lg shadow-red-500/50'
                  }`}>
                    <div className="absolute inset-0 rounded-full bg-white/30 blur-sm"></div>
                  </div>
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center backdrop-blur-sm">
                        <svg className="w-4 h-4 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                        </svg>
                      </div>
                      <span className="text-white font-bold text-base tracking-tight">WebSocket</span>
                    </div>
                    
                    <div className={`px-3 py-1 rounded-full text-xs font-bold backdrop-blur-sm border transition-all duration-300 ${
                      wsConnected 
                        ? 'bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-300 border-emerald-500/30 shadow-lg shadow-emerald-500/20' 
                        : 'bg-gradient-to-r from-red-500/20 to-rose-500/20 text-red-300 border-red-500/30'
                    }`}>
                      {wsConnected ? '● Conectado' : '● Desconectado'}
                    </div>
                  </div>
                  
                  {wsConnected && (
                    <div className="flex items-center gap-2 text-xs">
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shadow-lg shadow-cyan-400/50"></div>
                        <span className="text-gray-400 font-mono font-semibold">{ping}ms</span>
                      </div>
                      <span className="text-gray-500">•</span>
                      <span className={`text-xs font-semibold bg-gradient-to-r ${quality.gradient} bg-clip-text text-transparent`}>
                        {quality.icon} {quality.label}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Botón expand premium */}
              <div className={`w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center transition-all duration-300 group-hover:bg-white/10 group-hover:border-white/20 group-hover:scale-110 ${
                isExpanded ? 'rotate-180 bg-gradient-to-br from-cyan-500/20 to-purple-500/20' : ''
              }`}>
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          {/* Panel expandido */}
          <div className={`overflow-hidden transition-all duration-700 ease-out ${
            isExpanded ? 'max-h-[700px] opacity-100' : 'max-h-0 opacity-0'
          }`}>
            <div className="px-5 pb-5 space-y-4 border-t border-white/5">
              {/* Gráfica de latencia premium */}
              {wsConnected && (
                <div className="relative pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-white/10 flex items-center justify-center">
                        <svg className="w-3.5 h-3.5 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <span className="text-xs text-gray-300 font-semibold uppercase tracking-wider">Latencia</span>
                    </div>
                    <span className="text-lg font-bold text-white font-mono">{ping}ms</span>
                  </div>
                  
                  <div className="relative h-3 bg-white/5 rounded-full overflow-hidden border border-white/10 backdrop-blur-sm">
                    <div 
                      className={`h-full bg-gradient-to-r ${quality.gradient} transition-all duration-500 shadow-lg relative overflow-hidden`}
                      style={{ width: `${Math.min((ping / 50) * 100, 100)}%` }}
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                    </div>
                  </div>
                  
                  <div className="flex justify-between text-xs text-gray-500 mt-2 font-mono">
                    <span>0ms</span>
                    <span>50ms+</span>
                  </div>
                </div>
              )}

              {/* Stats grid premium */}
              <div className="grid grid-cols-2 gap-3">
                {/* Unidades activas */}
                <div className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300"></div>
                  <div className="relative bg-white/5 backdrop-blur-xl rounded-2xl p-4 border border-white/10 hover:border-cyan-500/30 transition-all duration-300 hover:bg-white/10">
                    <div className="flex items-start justify-between mb-2">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xl shadow-lg shadow-cyan-500/30 border border-white/10">
                        🚍
                      </div>
                      <div className={`px-2.5 py-1 rounded-full text-xs font-bold backdrop-blur-sm border ${
                        activeUnits > 0 
                          ? 'bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-300 border-emerald-500/30 shadow-lg shadow-emerald-500/20' 
                          : 'bg-white/5 text-gray-400 border-white/10'
                      }`}>
                        {activeUnits}/{totalUnits}
                      </div>
                    </div>
                    <div className="text-xs text-gray-400 mb-1 font-medium">Unidades</div>
                    <div className="text-2xl font-bold text-white mb-0.5">{activeUnits}</div>
                    <div className="text-xs text-gray-500">Activas</div>
                  </div>
                </div>

                {/* Eventos */}
                <div className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300"></div>
                  <div className="relative bg-white/5 backdrop-blur-xl rounded-2xl p-4 border border-white/10 hover:border-purple-500/30 transition-all duration-300 hover:bg-white/10">
                    <div className="flex items-start justify-between mb-2">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-xl shadow-lg shadow-purple-500/30 border border-white/10">
                        🚨
                      </div>
                      <div className="px-2.5 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300 border border-purple-500/30 shadow-lg shadow-purple-500/20 backdrop-blur-sm">
                        24h
                      </div>
                    </div>
                    <div className="text-xs text-gray-400 mb-1 font-medium">Eventos</div>
                    <div className="text-2xl font-bold text-white mb-0.5">{events.length}</div>
                    <div className="text-xs text-gray-500">Registrados</div>
                  </div>
                </div>
              </div>

              {/* Uptime y calidad premium */}
              {wsConnected && (
                <>
                  <div className="relative group">
                    <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-2xl blur-xl"></div>
                    <div className="relative bg-white/5 backdrop-blur-xl rounded-2xl p-4 border border-white/10">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-white/10 flex items-center justify-center">
                            <svg className="w-4 h-4 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </div>
                          <span className="text-xs text-gray-300 font-semibold uppercase tracking-wider">Tiempo Activo</span>
                        </div>
                        <span className="text-lg font-mono font-bold text-white">{formatUptime(uptime)}</span>
                      </div>
                      <div className="relative h-2 bg-white/5 rounded-full overflow-hidden border border-white/10">
                        <div className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 animate-pulse relative overflow-hidden">
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Calidad de conexión premium */}
                  <div className="relative group">
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl blur-xl"></div>
                    <div className="relative bg-gradient-to-r from-white/5 to-white/10 backdrop-blur-xl rounded-2xl p-4 border border-white/10">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full animate-pulse shadow-lg relative ${
                            quality.color === 'emerald' ? 'bg-emerald-500 shadow-emerald-500/50' :
                            quality.color === 'cyan' ? 'bg-cyan-500 shadow-cyan-500/50' :
                            quality.color === 'yellow' ? 'bg-yellow-500 shadow-yellow-500/50' :
                            'bg-orange-500 shadow-orange-500/50'
                          }`}>
                            <div className={`absolute inset-0 rounded-full animate-ping ${
                              quality.color === 'emerald' ? 'bg-emerald-500/30' :
                              quality.color === 'cyan' ? 'bg-cyan-500/30' :
                              quality.color === 'yellow' ? 'bg-yellow-500/30' :
                              'bg-orange-500/30'
                            }`} style={{ animationDuration: '2s' }}></div>
                          </div>
                          <span className="text-xs text-gray-300 font-semibold uppercase tracking-wider">Calidad</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{quality.icon}</span>
                          <span className={`text-base font-bold bg-gradient-to-r ${quality.gradient} bg-clip-text text-transparent`}>
                            {quality.label}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* Estado desconectado premium */}
              {!wsConnected && (
                <div className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-rose-500/10 rounded-2xl blur-xl"></div>
                  <div className="relative bg-gradient-to-r from-red-500/10 to-rose-500/10 backdrop-blur-xl rounded-2xl p-5 border border-red-500/30">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 flex items-center justify-center text-2xl flex-shrink-0 shadow-lg shadow-red-500/20">
                        ⚠️
                      </div>
                      <div className="flex-1">
                        <div className="text-base font-bold text-red-300 mb-2">Conexión Perdida</div>
                        <div className="text-sm text-gray-400 leading-relaxed mb-3">
                          Intentando reconectar automáticamente...
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin"></div>
                          <span className="text-sm text-red-400 font-medium">Reconectando...</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Información técnica premium */}
              {wsConnected && (
                <div className="pt-3 border-t border-white/5">
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500 font-medium">Protocolo</span>
                      <span className="text-gray-200 font-mono font-semibold bg-white/5 px-2 py-1 rounded-lg border border-white/10">WebSocket</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500 font-medium">Estado</span>
                      <span className="text-emerald-400 font-semibold flex items-center gap-1.5 bg-emerald-500/10 px-2 py-1 rounded-lg border border-emerald-500/20">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50"></span>
                        Ready
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500 font-medium">Servidor</span>
                      <span className="text-gray-200 font-mono font-semibold bg-white/5 px-2 py-1 rounded-lg border border-white/10">localhost:8000</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500 font-medium">Mensajes</span>
                      <span className="text-cyan-300 font-mono font-bold">{messagesCount}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  )
}

export default WebSocketMonitor

