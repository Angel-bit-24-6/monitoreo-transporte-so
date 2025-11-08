import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { loadEvents } from '../utils/api'

const EventsPanel = () => {
  const { events, setEvents, filters, setFilters, units } = useApp()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [expandedEvent, setExpandedEvent] = useState(null)

  // Cargar eventos inicialmente
  useEffect(() => {
    const fetchEvents = async () => {
      setIsLoading(true)
      try {
        const data = await loadEvents(filters)
        setEvents(data.map(event => ({
          id: event.id || event.event_id,
          unidad_id: event.unidad_id,
          tipo: event.tipo,
          detalle: event.detalle,
          timestamp: event.ts,
        })))
      } catch (error) {
        console.error('Error cargando eventos:', error)
      } finally {
        setIsLoading(false)
      }
    }
    fetchEvents()
  }, [])

  const handleApplyFilters = async () => {
    setIsLoading(true)
    try {
      const data = await loadEvents(filters)
      setEvents(data.map(event => ({
        id: event.id || event.event_id,
        unidad_id: event.unidad_id,
        tipo: event.tipo,
        detalle: event.detalle,
        timestamp: event.ts,
      })))
    } catch (error) {
      console.error('Error cargando eventos:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearFilters = async () => {
    const newFilters = {
      unidad_id: '',
      tipo: '',
      limit: 20,
    }
    setFilters(newFilters)
    setIsLoading(true)
    try {
      const data = await loadEvents(newFilters)
      setEvents(data.map(event => ({
        id: event.id || event.event_id,
        unidad_id: event.unidad_id,
        tipo: event.tipo,
        detalle: event.detalle,
        timestamp: event.ts,
      })))
    } catch (error) {
      console.error('Error cargando eventos:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const typeConfig = {
    'OUT_OF_BOUND': {
      name: 'Fuera de Ruta',
      icon: '🚨',
      gradient: 'from-red-500 via-rose-500 to-pink-600',
      bg: 'from-red-500/10 to-rose-500/5',
      border: 'border-red-500/30',
      glow: 'shadow-red-500/20',
      ring: 'ring-red-500/50',
      text: 'text-red-600'
    },
    'STOP_LONG': {
      name: 'Detención Prolongada',
      icon: '⏸️',
      gradient: 'from-amber-500 via-yellow-500 to-orange-500',
      bg: 'from-amber-500/10 to-yellow-500/5',
      border: 'border-amber-500/30',
      glow: 'shadow-amber-500/20',
      ring: 'ring-amber-500/50',
      text: 'text-amber-600'
    },
    'SPEEDING': {
      name: 'Exceso de Velocidad',
      icon: '⚡',
      gradient: 'from-orange-500 via-red-500 to-rose-600',
      bg: 'from-orange-500/10 to-red-500/5',
      border: 'border-orange-500/30',
      glow: 'shadow-orange-500/20',
      ring: 'ring-orange-500/50',
      text: 'text-orange-600'
    },
    'GENERAL_ALERT': {
      name: 'Alerta General',
      icon: '⚠️',
      gradient: 'from-blue-500 via-indigo-500 to-purple-600',
      bg: 'from-blue-500/10 to-indigo-500/5',
      border: 'border-blue-500/30',
      glow: 'shadow-blue-500/20',
      ring: 'ring-blue-500/50',
      text: 'text-blue-600'
    }
  }

  const getEventConfig = (tipo) => {
    return typeConfig[tipo] || typeConfig['GENERAL_ALERT']
  }

  return (
    <div 
      className={`events-panel absolute top-4 right-4 w-[420px] max-h-[92vh] rounded-2xl overflow-hidden z-[1000] flex flex-col transition-all duration-500 ease-out ${
        isCollapsed ? 'max-h-[70px]' : ''
      }`}
      id="events-panel"
    >
      {/* Fondo con glassmorphism */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-2xl"></div>
      
      {/* Orbes de fondo */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>

      {/* Borde luminoso */}
      <div className="absolute inset-0 rounded-2xl border border-white/10 pointer-events-none"></div>
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-400/50 to-transparent"></div>

      {/* Contenido */}
      <div className="relative z-10 flex flex-col h-full">
        {/* Header Premium */}
        <div 
          className="events-header p-6 cursor-pointer select-none relative overflow-hidden group transition-all duration-300"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {/* Fondo con gradiente animado */}
          <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 via-blue-600/20 to-indigo-600/20 group-hover:from-purple-600/30 group-hover:via-blue-600/30 group-hover:to-indigo-600/30 transition-all duration-300"></div>
          
          {/* Efecto de brillo en hover */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>

          <div className="relative z-10 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Icono con efecto pulsante */}
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/30 to-blue-500/30 rounded-xl blur-md animate-pulse"></div>
                <div className="relative w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center shadow-lg shadow-purple-500/50">
                  <span className="text-2xl">📋</span>
                </div>
              </div>

              <div>
                <h2 className="text-xl font-bold text-transparent bg-gradient-to-r from-purple-300 via-blue-300 to-indigo-300 bg-clip-text">
                  Eventos del Sistema
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">Monitor en tiempo real</p>
              </div>
            </div>

            {/* Botón collapse animado */}
            <div className="flex items-center gap-3">
              {!isCollapsed && (
                <div className="px-3 py-1 rounded-full bg-purple-500/20 border border-purple-500/30 text-xs font-semibold text-purple-300">
                  {events.length}
                </div>
              )}
              <div className={`w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center transition-transform duration-300 group-hover:bg-white/10 ${
                isCollapsed ? 'rotate-180' : ''
              }`}>
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {!isCollapsed && (
          <>
            {/* Panel de filtros mejorado */}
            <div className="filters-panel p-6 border-y border-white/5 bg-black/20">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-1 h-6 rounded-full bg-gradient-to-b from-purple-500 to-blue-500"></div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Filtros Avanzados</h3>
              </div>

              <div className="space-y-3">
                {/* Filtro de Unidad */}
                <div className="filter-group">
                  <label className="block text-xs text-gray-400 mb-2 font-medium" htmlFor="filter-unit">
                    🚍 Unidad
                  </label>
                  <div className="relative group">
                    {/* Fondo con gradiente sutil */}
                    <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-indigo-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>
                    
                    {/* Select personalizado */}
                    <select
                      id="filter-unit"
                      className="relative w-full p-3 pl-12 pr-10 rounded-xl text-sm bg-white/5 text-white border border-white/10 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all duration-200 hover:bg-white/10 hover:border-white/20 appearance-none cursor-pointer backdrop-blur-sm z-10"
                      value={filters.unidad_id}
                      onChange={(e) => setFilters({ ...filters, unidad_id: e.target.value })}
                    >
                      <option value="" className="bg-slate-900 text-white">Todas las unidades</option>
                      {Object.values(units).map(unit => (
                        <option key={unit.id} value={unit.id} className="bg-slate-900 text-white">
                          {unit.id} - {unit.placa || 'Sin placa'}
                        </option>
                      ))}
                    </select>
                    
                    {/* Icono izquierdo */}
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none z-20">
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center border border-white/10">
                        <svg className="w-3.5 h-3.5 text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                    </div>
                    
                    {/* Icono flecha derecha */}
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none z-20">
                      <div className="w-6 h-6 rounded-lg bg-white/5 flex items-center justify-center border border-white/10 group-hover:bg-white/10 transition-colors">
                        <svg className="w-3.5 h-3.5 text-gray-300 group-hover:text-purple-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Filtro de Tipo */}
                <div className="filter-group">
                  <label className="block text-xs text-gray-400 mb-2 font-medium" htmlFor="filter-type">
                    🔔 Tipo de Evento
                  </label>
                  <div className="relative group">
                    {/* Fondo con gradiente sutil */}
                    <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-indigo-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>
                    
                    {/* Select personalizado */}
                    <select
                      id="filter-type"
                      className="relative w-full p-3 pl-12 pr-10 rounded-xl text-sm bg-white/5 text-white border border-white/10 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all duration-200 hover:bg-white/10 hover:border-white/20 appearance-none cursor-pointer backdrop-blur-sm z-10"
                      value={filters.tipo}
                      onChange={(e) => setFilters({ ...filters, tipo: e.target.value })}
                    >
                      <option value="" className="bg-slate-900 text-white">Todos los tipos</option>
                      {Object.entries(typeConfig).map(([key, config]) => (
                        <option key={key} value={key} className="bg-slate-900 text-white">
                          {config.icon} {config.name}
                        </option>
                      ))}
                    </select>
                    
                    {/* Icono izquierdo */}
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none z-20">
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500/20 to-indigo-500/20 flex items-center justify-center border border-white/10">
                        <svg className="w-3.5 h-3.5 text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                        </svg>
                      </div>
                    </div>
                    
                    {/* Icono flecha derecha */}
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none z-20">
                      <div className="w-6 h-6 rounded-lg bg-white/5 flex items-center justify-center border border-white/10 group-hover:bg-white/10 transition-colors">
                        <svg className="w-3.5 h-3.5 text-gray-300 group-hover:text-blue-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Filtro de Cantidad */}
                <div className="filter-group">
                  <label className="block text-xs text-gray-400 mb-2 font-medium" htmlFor="filter-limit">
                    📊 Límite de Resultados
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {[20, 50, 100, 200].map(limit => (
                      <button
                        key={limit}
                        onClick={() => setFilters({ ...filters, limit })}
                        className={`p-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
                          filters.limit === limit
                            ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg shadow-purple-500/30'
                            : 'bg-white/5 text-gray-400 hover:bg-white/10 border border-white/10'
                        }`}
                      >
                        {limit}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Botones de acción */}
                <div className="flex gap-3 mt-5">
                  <button
                    className="flex-1 px-4 py-3 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 transition-all duration-200 shadow-lg shadow-purple-500/30 hover:shadow-purple-500/50 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={handleApplyFilters}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                        Cargando...
                      </span>
                    ) : (
                      '✓ Aplicar Filtros'
                    )}
                  </button>
                  <button
                    className="px-4 py-3 rounded-xl text-sm font-bold text-gray-300 bg-white/5 border border-white/10 hover:bg-white/10 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={handleClearFilters}
                    disabled={isLoading}
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>

            {/* Stats Bar */}
            <div className="p-4 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-indigo-500/10 border-b border-white/5">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-lg shadow-green-500/50"></div>
                  <span className="text-gray-300 font-medium">
                    Total: <span className="text-white font-bold">{events.length}</span> eventos
                  </span>
                </div>
                {filters.unidad_id && (
                  <div className="px-3 py-1 rounded-full bg-blue-500/20 border border-blue-500/30 text-xs font-semibold text-blue-300">
                    Unidad {filters.unidad_id}
                  </div>
                )}
              </div>
            </div>

            {/* Lista de eventos */}
            <div className="events-list flex-1 overflow-y-auto min-h-[300px] p-4 space-y-3">
              {isLoading ? (
                <div className="text-center py-16">
                  <div className="inline-block w-16 h-16 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin mb-4"></div>
                  <div className="text-gray-400 font-medium">Cargando eventos...</div>
                  <div className="text-xs text-gray-500 mt-1">Esto puede tomar unos segundos</div>
                </div>
              ) : events.length === 0 ? (
                <div className="text-center py-16">
                  <div className="text-6xl mb-4 opacity-30">📭</div>
                  <div className="text-gray-400 font-semibold text-lg mb-2">No hay eventos</div>
                  <div className="text-xs text-gray-500">Ajusta los filtros para ver más resultados</div>
                </div>
              ) : (
                events.map((event, index) => {
                  const config = getEventConfig(event.tipo)
                  const isExpanded = expandedEvent === event.id

                  return (
                    <div
                      key={event.id || index}
                      className={`event-item relative overflow-hidden rounded-xl transition-all duration-300 hover:scale-[1.02] cursor-pointer`}
                      onClick={() => setExpandedEvent(isExpanded ? null : event.id)}
                      style={{
                        animation: `slideInRight 0.4s ease-out ${index * 0.05}s both`
                      }}
                    >
                      {/* Fondo con gradiente */}
                      <div className={`absolute inset-0 bg-gradient-to-r ${config.bg} backdrop-blur-sm`}></div>
                      
                      {/* Borde lateral colorido */}
                      <div className={`absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b ${config.gradient}`}></div>

                      {/* Contenido */}
                      <div className={`relative z-10 p-4 border ${config.border} rounded-xl ${config.glow} shadow-lg hover:shadow-xl transition-all duration-300`}>
                        <div className="flex items-start justify-between gap-3">
                          {/* Icono y tipo */}
                          <div className="flex items-start gap-3 flex-1">
                            <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${config.gradient} flex items-center justify-center text-xl shadow-lg ${config.glow} flex-shrink-0`}>
                              {config.icon}
                            </div>

                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-bold text-white text-sm">
                                  {config.name}
                                </h4>
                                <div className={`px-2 py-0.5 rounded-full text-xs font-semibold ${config.bg} ${config.text} border ${config.border}`}>
                                  {event.unidad_id}
                                </div>
                              </div>

                              <div className="text-xs text-gray-400 flex items-center gap-2 mb-2">
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {new Date(event.timestamp).toLocaleString('es-MX', { 
                                  day: '2-digit',
                                  month: 'short',
                                  hour: '2-digit', 
                                  minute: '2-digit',
                                  second: '2-digit'
                                })}
                              </div>

                              {/* Detalle expandible */}
                              <div className={`overflow-hidden transition-all duration-300 ${
                                isExpanded ? 'max-h-40 opacity-100 mt-2' : 'max-h-0 opacity-0'
                              }`}>
                                <div className="text-sm text-gray-300 leading-relaxed p-3 rounded-lg bg-black/20 border border-white/5">
                                  {event.detalle}
                                </div>
                              </div>

                              {!isExpanded && (
                                <p className="text-xs text-gray-400 line-clamp-1">
                                  {event.detalle}
                                </p>
                              )}
                            </div>
                          </div>

                          {/* Indicador de expansión */}
                          <div className={`w-6 h-6 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 transition-transform duration-300 ${
                            isExpanded ? 'rotate-180' : ''
                          }`}>
                            <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes slideInRight {
          from {
            opacity: 0;
            transform: translateX(30px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        .events-list::-webkit-scrollbar {
          width: 8px;
        }

        .events-list::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 10px;
        }

        .events-list::-webkit-scrollbar-thumb {
          background: linear-gradient(to bottom, #a855f7, #3b82f6);
          border-radius: 10px;
        }

        .events-list::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(to bottom, #9333ea, #2563eb);
        }
      `}</style>
    </div>
  )
}

export default EventsPanel