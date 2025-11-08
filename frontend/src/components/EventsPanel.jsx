import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { loadEvents } from '../utils/api'

const EventsPanel = () => {
  const { events, setEvents, filters, setFilters, units } = useApp()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

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
  }, []) // Solo al montar

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

  const typeNames = {
    'OUT_OF_BOUND': '🚨 Fuera de Ruta',
    'STOP_LONG': '⏸️ Detención Prolongada',
    'SPEEDING': '⚡ Exceso de Velocidad',
    'GENERAL_ALERT': '⚠️ Alerta General',
  }

  const typeColors = {
    'OUT_OF_BOUND': 'from-red-500 via-red-600 to-red-700 border-red-500',
    'STOP_LONG': 'from-yellow-500 via-yellow-600 to-orange-600 border-yellow-500',
    'SPEEDING': 'from-orange-500 via-orange-600 to-red-600 border-orange-500',
    'GENERAL_ALERT': 'from-blue-500 via-blue-600 to-indigo-600 border-blue-500',
  }

  const getEventColor = (tipo) => {
    return typeColors[tipo] || 'from-gray-500 via-gray-600 to-gray-700 border-gray-500'
  }

  return (
    <div 
      className={`events-panel absolute top-4 right-4 w-[380px] max-h-[90vh] bg-gradient-to-b from-white to-gray-50 rounded-xl shadow-2xl overflow-hidden z-[1000] flex flex-col transition-all duration-300 ${
        isCollapsed ? 'max-h-[60px]' : ''
      }`}
      id="events-panel"
    >
      {/* Header con gradiente animado */}
      <div 
        className="events-header p-5 bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600 text-white font-bold flex-shrink-0 flex justify-between items-center cursor-pointer select-none relative overflow-hidden group transition-all duration-300 hover:from-blue-600 hover:via-blue-700 hover:to-indigo-700"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-white/10 via-transparent to-white/10 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
        <div className="relative z-10 flex items-center gap-3">
          <span className="text-2xl animate-pulse">📋</span>
          <span className="text-lg">Eventos Recientes</span>
        </div>
        <span className={`collapse-icon text-2xl transition-transform duration-300 relative z-10 ${
          isCollapsed ? 'rotate-180' : ''
        }`}>▼</span>
      </div>

      {!isCollapsed && (
        <>
          {/* Panel de filtros con gradiente */}
          <div className="filters-panel p-5 bg-gradient-to-br from-slate-800 via-slate-700 to-slate-800 border-b-2 border-slate-600 flex-shrink-0">
            <div className="filters-header text-base font-bold mb-4 text-white flex items-center gap-2">
              <span className="text-xl">🔍</span>
              <span>Filtros</span>
            </div>

            <div className="space-y-4">
              <div className="filter-group">
                <label className="block text-xs text-gray-300 mb-2 font-semibold uppercase tracking-wide" htmlFor="filter-unit">
                  Unidad
                </label>
                <select
                  id="filter-unit"
                  className="w-full p-3 border-2 border-slate-600 rounded-lg text-sm bg-slate-900 text-gray-100 focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/50 transition-all duration-200 hover:border-slate-500"
                  value={filters.unidad_id}
                  onChange={(e) => setFilters({ ...filters, unidad_id: e.target.value })}
                >
                  <option value="">Todas las unidades</option>
                  {Object.values(units).map(unit => (
                    <option key={unit.id} value={unit.id}>
                      {unit.id} - {unit.placa || 'Sin placa'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label className="block text-xs text-gray-300 mb-2 font-semibold uppercase tracking-wide" htmlFor="filter-type">
                  Tipo de Evento
                </label>
                <select
                  id="filter-type"
                  className="w-full p-3 border-2 border-slate-600 rounded-lg text-sm bg-slate-900 text-gray-100 focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/50 transition-all duration-200 hover:border-slate-500"
                  value={filters.tipo}
                  onChange={(e) => setFilters({ ...filters, tipo: e.target.value })}
                >
                  <option value="">Todos los tipos</option>
                  <option value="OUT_OF_BOUND">🚨 Fuera de Ruta</option>
                  <option value="STOP_LONG">⏸️ Detención Prolongada</option>
                  <option value="SPEEDING">⚡ Exceso de Velocidad</option>
                  <option value="GENERAL_ALERT">⚠️ Alerta General</option>
                </select>
              </div>

              <div className="filter-group">
                <label className="block text-xs text-gray-300 mb-2 font-semibold uppercase tracking-wide" htmlFor="filter-limit">
                  Cantidad
                </label>
                <select
                  id="filter-limit"
                  className="w-full p-3 border-2 border-slate-600 rounded-lg text-sm bg-slate-900 text-gray-100 focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/50 transition-all duration-200 hover:border-slate-500"
                  value={filters.limit}
                  onChange={(e) => setFilters({ ...filters, limit: parseInt(e.target.value) })}
                >
                  <option value="20">20 eventos</option>
                  <option value="50">50 eventos</option>
                  <option value="100">100 eventos</option>
                  <option value="200">200 eventos</option>
                </select>
              </div>

              <div className="filter-buttons flex gap-3 mt-5">
                <button
                  className="flex-1 px-4 py-3 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-600 hover:to-cyan-600 transition-all duration-200 shadow-lg shadow-teal-500/30 hover:shadow-teal-500/50 hover:scale-[1.02] active:scale-[0.98]"
                  onClick={handleApplyFilters}
                  disabled={isLoading}
                >
                  {isLoading ? '⏳ Aplicando...' : '✓ Aplicar'}
                </button>
                <button
                  className="flex-1 px-4 py-3 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800 transition-all duration-200 shadow-lg shadow-gray-500/30 hover:shadow-gray-500/50 hover:scale-[1.02] active:scale-[0.98]"
                  onClick={handleClearFilters}
                  disabled={isLoading}
                >
                  ✕ Limpiar
                </button>
              </div>
            </div>
          </div>

          {/* Contador de eventos con gradiente */}
          <div className="events-count text-sm text-gray-700 p-3 bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border-b-2 border-gray-200 flex-shrink-0 flex items-center justify-between">
            <span className="font-semibold">
              <span className="text-blue-600 font-bold">{events.length}</span> eventos
            </span>
            {filters.unidad_id && (
              <span className="text-xs text-gray-500">
                Unidad: {filters.unidad_id}
              </span>
            )}
          </div>

          {/* Lista de eventos */}
          <div className="events-list flex-1 overflow-y-auto custom-scrollbar min-h-[200px] bg-gradient-to-b from-white to-gray-50">
            {isLoading ? (
              <div className="text-center p-8">
                <div className="inline-block animate-spin text-4xl mb-3">⏳</div>
                <div className="text-gray-500">Cargando eventos...</div>
              </div>
            ) : events.length === 0 ? (
              <div className="text-center p-8">
                <div className="text-5xl mb-3 opacity-50">📭</div>
                <div className="text-gray-400 font-medium">Sin eventos</div>
                <div className="text-xs text-gray-400 mt-2">No hay eventos que coincidan con los filtros</div>
              </div>
            ) : (
              events.map((event, index) => (
                <div
                  key={event.id || index}
                  className={`event-item p-4 border-b border-gray-200/50 relative overflow-hidden group transition-all duration-300 hover:bg-gray-50 hover:shadow-md slide-in-animation ${
                    event.tipo === 'OUT_OF_BOUND' ? 'border-l-4 border-l-red-500' :
                    event.tipo === 'STOP_LONG' ? 'border-l-4 border-l-yellow-500' :
                    event.tipo === 'SPEEDING' ? 'border-l-4 border-l-orange-500' :
                    'border-l-4 border-l-blue-500'
                  }`}
                  style={{
                    animationDelay: `${index * 0.05}s`,
                  }}
                >
                  {/* Efecto de brillo en hover */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                  
                  {/* Indicador de tipo con gradiente */}
                  <div className={`absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b ${getEventColor(event.tipo)}`}></div>

                  <div className="relative z-10">
                    {/* Header del evento */}
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{event.tipo === 'OUT_OF_BOUND' ? '🚨' : event.tipo === 'STOP_LONG' ? '⏸️' : event.tipo === 'SPEEDING' ? '⚡' : '⚠️'}</span>
                        <div>
                          <div className="event-type font-bold text-sm text-gray-800">
                            {typeNames[event.tipo] || event.tipo}
                          </div>
                          <div className="event-time text-xs text-gray-500 mt-0.5">
                            {new Date(event.timestamp).toLocaleTimeString('es-MX', { 
                              hour: '2-digit', 
                              minute: '2-digit',
                              second: '2-digit'
                            })}
                          </div>
                        </div>
                      </div>
                      <div className="text-xs font-semibold px-2 py-1 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
                        {event.unidad_id}
                      </div>
                    </div>

                    {/* Detalle del evento */}
                    <div className="event-detail text-sm text-gray-700 leading-relaxed pl-8">
                      {event.detalle}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default EventsPanel

