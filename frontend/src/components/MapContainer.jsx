import { useRef } from 'react'
import { useApp } from '../context/AppContext'
import { useLeaflet } from '../hooks/useLeaflet'
import { useWebSocket } from '../hooks/useWebSocket'

const MapContainer = ({ children }) => {
  // Inicializar Leaflet (usa getElementById('map') internamente)
  useLeaflet()
  
  // Inicializar WebSocket
  useWebSocket()

  return (
    <div 
      className="map-container flex-1 relative" 
      style={{ 
        height: '100vh', 
        width: '100%', 
        position: 'relative',
        minHeight: 0,
        flex: '1 1 0%'
      }}
    >
      <div 
        id="map" 
        className="w-full h-full leaflet-container" 
        style={{ 
          height: '100%', 
          width: '100%'
        }}
      ></div>
      {children}
    </div>
  )
}

export default MapContainer

