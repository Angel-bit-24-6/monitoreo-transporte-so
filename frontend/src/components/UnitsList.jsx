import { useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { loadUnits } from '../utils/api'

const UnitsList = ({ onSelectUnit }) => {
  const { units, setUnits, selectedUnit, setSelectedUnit, map } = useApp()

  useEffect(() => {
    const fetchUnits = async () => {
      const data = await loadUnits()
      if (data) {
        const unitsObj = {}
        data.forEach(unit => {
          unitsObj[unit.id] = {
            ...unit,
            is_connected: false,
            last_position: null,
          }
        })
        setUnits(unitsObj)
      }
    }

    fetchUnits()
  }, [setUnits])

  const handleSelectUnit = (unitId) => {
    setSelectedUnit(unitId)
    
    // Centrar mapa en la unidad
    const unit = units[unitId]
    if (map && unit?.last_position) {
      map.setView([unit.last_position.lat, unit.last_position.lon], 15)
    }

    // Cerrar sidebar en móviles
    if (onSelectUnit && window.innerWidth <= 767) {
      onSelectUnit()
    }
  }

  if (Object.keys(units).length === 0) {
    return (
      <div className="text-center p-5 text-gray-400">
        Cargando unidades...
      </div>
    )
  }

  return (
    <div 
      className="units-list flex-1 overflow-y-auto custom-scrollbar" 
      id="units-list"
    >
      {Object.values(units).map((unit, index) => {
        const isOnline = unit.is_connected
        const speed = unit.last_position?.speed
          ? `${(unit.last_position.speed * 3.6).toFixed(1)} km/h`
          : 'N/A'
        const isSelected = selectedUnit === unit.id

        return (
          <div
            key={unit.id}
            className={`unit-item p-5 cursor-pointer transition-all duration-300 relative overflow-hidden group border-b border-slate-700/10 slide-in-animation ${
              isSelected 
                ? 'bg-gradient-to-r from-teal-500 via-cyan-500 to-blue-500 shadow-lg shadow-teal-500/30 scale-[1.02]' 
                : 'bg-slate-800/50 hover:bg-slate-700/80 hover:scale-[1.01]'
            } ${!isOnline ? 'opacity-70' : ''}`}
            data-unit-id={unit.id}
            onClick={() => handleSelectUnit(unit.id)}
            style={{
              animationDelay: `${index * 0.1}s`,
            }}
          >
            {/* Efecto de brillo en hover */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
            
            {/* Indicador lateral animado cuando está seleccionado */}
            {isSelected && (
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-white rounded-r-full animate-pulse"></div>
            )}

            <div className="relative z-10">
              {/* Header con ID y estado */}
              <div className="flex justify-between items-center mb-3">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                    isOnline ? 'bg-green-400 shadow-lg shadow-green-400/50 animate-pulse' : 'bg-red-400'
                  }`}></div>
                  <span className="font-bold text-lg text-white transition-colors duration-300">
                    {unit.id}
                  </span>
                </div>
                <span 
                  className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-all duration-300 ${
                    isOnline 
                      ? 'bg-green-500/20 text-green-300 border border-green-500/30 shadow-lg shadow-green-500/20' 
                      : 'bg-red-500/20 text-red-300 border border-red-500/30'
                  }`}
                >
                  {isOnline ? '● En línea' : '● Offline'}
                </span>
              </div>

              {/* Información de la unidad */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <span className="text-lg">🚗</span>
                  <span className={isSelected ? 'text-white font-medium' : ''}>
                    {unit.placa || 'Sin placa'}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <span className="text-lg">👤</span>
                  <span className={isSelected ? 'text-white font-medium' : ''}>
                    {unit.chofer || 'Sin chofer'}
                  </span>
                </div>
                <div className={`flex items-center gap-2 mt-3 pt-3 border-t ${
                  isSelected ? 'border-white/20' : 'border-gray-600/30'
                }`}>
                  <span className="text-xl animate-pulse">⚡</span>
                  <span className={`text-base font-bold transition-colors duration-300 ${
                    isSelected ? 'text-white' : 'text-cyan-400'
                  }`}>
                    {speed}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default UnitsList

