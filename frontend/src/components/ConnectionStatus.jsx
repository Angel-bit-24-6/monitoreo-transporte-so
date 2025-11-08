import { useApp } from '../context/AppContext'

const ConnectionStatus = () => {
  const { wsConnected } = useApp()

  return (
    <div 
      className={`connection-status p-4 flex items-center gap-3 relative overflow-hidden ${
        wsConnected 
          ? 'bg-gradient-to-br from-green-500/10 via-green-600/15 to-green-500/10 border-l-4 border-green-500' 
          : 'bg-gradient-to-br from-red-500/10 via-red-600/15 to-red-500/10 border-l-4 border-red-500'
      }`}
    >
      {/* Efecto de brillo animado */}
      <div 
        className={`absolute inset-0 shimmer-animation ${
          wsConnected ? 'bg-gradient-to-r from-green-500/20 to-transparent' : 'bg-gradient-to-r from-red-500/20 to-transparent'
        } animate-pulse`}
      ></div>
      
      <div className="relative z-10 flex items-center gap-3">
        {/* Indicador de estado animado */}
        <div className="relative">
          <div 
            className={`status-dot w-4 h-4 rounded-full transition-all duration-300 ${
              wsConnected 
                ? 'bg-green-500 shadow-lg shadow-green-500/50 animate-pulse' 
                : 'bg-red-500 shadow-lg shadow-red-500/50'
            }`}
            id="ws-status-dot"
          />
          {wsConnected && (
            <div className="absolute inset-0 rounded-full bg-green-500 opacity-75 animate-ping [animation-duration:2s]"></div>
          )}
        </div>
        
        <div className="flex flex-col">
          <span 
            className={`text-sm font-semibold transition-all duration-300 ${
              wsConnected ? 'text-green-400' : 'text-red-400'
            }`}
            id="ws-status-text"
          >
            {wsConnected ? 'Conectado' : 'Desconectado'}
          </span>
          <span className="text-xs text-gray-400">
            {wsConnected ? 'Sincronización activa' : 'Reintentando conexión...'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default ConnectionStatus

