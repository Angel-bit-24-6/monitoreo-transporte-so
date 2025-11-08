import { useEffect, useRef, useCallback } from 'react'
import { useApp } from '../context/AppContext'

export const useWebSocket = () => {
  const { ws, setWs, wsConnected, setWsConnected, units, setUnits, setEvents, map, markersRef } = useApp()
  const reconnectTimeoutRef = useRef(null)

  // Función helper para crear icono SVG premium
  const createPremiumBusIcon = useCallback((isOnline) => {
    const color = isOnline ? '#10b981' : '#ef4444'
    const borderColor = isOnline ? '#34d399' : '#f87171'
    const darkColor = isOnline ? '#059669' : '#dc2626'
    const pulseAnim = isOnline ? 'busPulse 2s infinite' : 'none'
    
    // Crear un ID único para evitar conflictos de estilos
    const iconId = `bus-icon-${isOnline ? 'online' : 'offline'}-${Date.now()}`
    
    const busIconSVG = `
      <div class="custom-bus-icon-wrapper" style="position: relative; width: 40px; height: 40px; z-index: 1000;">
        <div style="position: absolute; inset: -4px; background: radial-gradient(circle, ${color}40 0%, transparent 70%); border-radius: 50%; animation: ${pulseAnim};"></div>
        <div style="position: absolute; inset: 0; background: linear-gradient(135deg, ${color} 0%, ${darkColor} 100%); border-radius: 50%; border: 3px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.3), 0 0 0 2px ${borderColor}40, inset 0 1px 0 rgba(255,255,255,0.3);"></div>
        <svg style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 24px; height: 24px; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2)); pointer-events: none;" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="3" y="6" width="18" height="10" rx="1.5" fill="white" opacity="0.95"/>
          <rect x="5" y="8" width="3" height="2.5" rx="0.5" fill="${color}" opacity="0.3"/>
          <rect x="9.5" y="8" width="3" height="2.5" rx="0.5" fill="${color}" opacity="0.3"/>
          <rect x="14" y="8" width="3" height="2.5" rx="0.5" fill="${color}" opacity="0.3"/>
          <circle cx="7" cy="17" r="2.5" fill="white" opacity="0.9"/>
          <circle cx="17" cy="17" r="2.5" fill="white" opacity="0.9"/>
          <circle cx="7" cy="17" r="1.5" fill="${color}" opacity="0.4"/>
          <circle cx="17" cy="17" r="1.5" fill="${color}" opacity="0.4"/>
          <line x1="3" y1="11" x2="21" y2="11" stroke="${color}" stroke-width="1.5" opacity="0.4"/>
        </svg>
        <div style="position: absolute; top: 2px; right: 2px; width: 8px; height: 8px; background: ${color}; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 0 2px ${borderColor}40, 0 0 8px ${color}80; animation: ${pulseAnim};"></div>
      </div>
    `
    
    return L.divIcon({
      className: 'custom-bus-icon',
      html: busIconSVG,
      iconSize: [40, 40],
      iconAnchor: [20, 20],
      popupAnchor: [0, -20],
    })
  }, [])

  // Función para manejar actualizaciones de posición
  const handlePositionUpdate = useCallback((data) => {
    const { unidad_id, lat, lon, speed, heading, timestamp } = data

    console.log(`📍 POSITION_UPDATE recibido: ${unidad_id} en [${lat}, ${lon}]`)

    // Actualizar estado de unidad y crear/actualizar marcador
    setUnits(prev => {
      const updated = { ...prev }
      let unit
      
      if (updated[unidad_id]) {
        updated[unidad_id] = {
          ...updated[unidad_id],
          last_position: { lat, lon, speed, heading, timestamp },
        }
        unit = updated[unidad_id]
      } else {
        // Crear unidad si no existe
        unit = {
          id: unidad_id,
          placa: null,
          chofer: null,
          is_connected: true,
          last_position: { lat, lon, speed, heading, timestamp },
        }
        updated[unidad_id] = unit
        console.log(`✓ Unidad creada: ${unidad_id}`)
      }

      // Actualizar o crear marcador en el mapa (usar el estado actualizado)
      if (map && typeof L !== 'undefined') {
        const isOnline = unit?.is_connected !== false
        
        if (markersRef.current[unidad_id]) {
          // Actualizar posición del marcador existente
          markersRef.current[unidad_id].setLatLng([lat, lon])
          
          // Actualizar icono con el estado actual
          const newIcon = createPremiumBusIcon(isOnline)
          markersRef.current[unidad_id].setIcon(newIcon)
          
          // Actualizar popup con nueva velocidad
          const popupContent = `
            <div class="unit-popup">
              <div class="popup-header">${unidad_id}</div>
              <div class="popup-info">
                <div><strong>Placa:</strong> ${unit?.placa || 'N/A'}</div>
                <div><strong>Chofer:</strong> ${unit?.chofer || 'N/A'}</div>
                <div><strong>Velocidad:</strong> ${speed ? (speed * 3.6).toFixed(1) : 'N/A'} km/h</div>
                <div><strong>Última actualización:</strong> ${new Date(timestamp).toLocaleTimeString()}</div>
              </div>
            </div>
          `
          markersRef.current[unidad_id].setPopupContent(popupContent)
        } else {
          // Crear nuevo marcador con icono SVG premium
          console.log(`🎯 Creando marcador para ${unidad_id} en [${lat}, ${lon}], mapa disponible:`, !!map)
          
          const icon = createPremiumBusIcon(isOnline)
          const marker = L.marker([lat, lon], { icon }).addTo(map)
          
          const popupContent = `
            <div class="unit-popup">
              <div class="popup-header">${unidad_id}</div>
              <div class="popup-info">
                <div><strong>Placa:</strong> ${unit?.placa || 'N/A'}</div>
                <div><strong>Chofer:</strong> ${unit?.chofer || 'N/A'}</div>
                <div><strong>Velocidad:</strong> ${speed ? (speed * 3.6).toFixed(1) : 'N/A'} km/h</div>
                <div><strong>Última actualización:</strong> ${new Date(timestamp).toLocaleTimeString()}</div>
              </div>
            </div>
          `
          marker.bindPopup(popupContent)
          markersRef.current[unidad_id] = marker
          console.log(`✓ Marcador creado para ${unidad_id} en [${lat}, ${lon}]`, marker)
        }
      } else {
        console.warn(`⚠️ No se puede crear marcador: mapa=${!!map}, L=${typeof L !== 'undefined'}`)
      }

      return updated
    })
  }, [map, markersRef, setUnits, createPremiumBusIcon])

  // Función para manejar alertas de eventos
  const handleEventAlert = useCallback((data) => {
    const { unidad_id, event_tipo, detalle, timestamp, event_id } = data

    console.log(`🚨 Evento: ${event_tipo} - ${unidad_id} (ID: ${event_id})`)

    // Agregar evento a la lista
    setEvents(prev => [
      {
        id: event_id,
        unidad_id,
        tipo: event_tipo,
        detalle,
        timestamp,
      },
      ...prev.slice(0, 19), // Mantener solo los últimos 20
    ])

    // Mostrar popup en el marcador
    if (markersRef.current[unidad_id]) {
      markersRef.current[unidad_id].openPopup()
    }
  }, [markersRef, setEvents])

  // Función para manejar cambios de estado de conexión
  const handleConnectionState = useCallback((data) => {
    const { unidad_id, is_connected } = data

    setUnits(prev => {
      const updated = { ...prev }
      if (updated[unidad_id]) {
        updated[unidad_id] = {
          ...updated[unidad_id],
          is_connected,
        }
      }
      return updated
    })

    // Actualizar icono del marcador con SVG premium
    if (map && typeof L !== 'undefined' && markersRef.current[unidad_id]) {
      const newIcon = createPremiumBusIcon(is_connected)
      markersRef.current[unidad_id].setIcon(newIcon)
    }
  }, [map, markersRef, setUnits, createPremiumBusIcon])

  // Función para manejar mensajes WebSocket
  const handleWebSocketMessage = useCallback((message) => {
    console.log('📨 Mensaje WebSocket recibido:', message.type, message)
    switch (message.type) {
      case 'POSITION_UPDATE':
        handlePositionUpdate(message)
        break
      case 'EVENT_ALERT':
        handleEventAlert(message)
        break
      case 'CONNECTION_STATE':
        handleConnectionState(message)
        break
      case 'SUBSCRIBED':
        console.log(`✓ Confirmación de suscripción: ${message.message}`)
        break
      case 'PONG':
        // Heartbeat response
        break
      default:
        console.log('Mensaje desconocido:', message)
    }
  }, [handlePositionUpdate, handleEventAlert, handleConnectionState])

  useEffect(() => {
    // No conectar si no hay mapa disponible
    if (!map) {
      console.log('⏳ Esperando mapa para conectar WebSocket...')
      return
    }

    if (ws) return // Ya está conectado

    const WS_URL = 'ws://localhost:8000/ws/dashboard'
    console.log('Conectando WebSocket...')

    const websocket = new WebSocket(WS_URL)

    websocket.onopen = () => {
      console.log('✓ WebSocket conectado')
      setWsConnected(true)
      setWs(websocket)

      // Suscribirse a todas las unidades después de un pequeño delay
      // Usar una función que acceda al estado actual
      setTimeout(() => {
        setUnits(currentUnits => {
          const unidadIds = Object.keys(currentUnits)
          if (unidadIds.length > 0 && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
              type: 'SUBSCRIBE',
              unidad_ids: unidadIds,
            }))
            console.log(`✓ Suscrito a ${unidadIds.length} unidades:`, unidadIds)
          } else if (unidadIds.length === 0) {
            console.log('⚠️ No hay unidades cargadas aún para suscribirse')
          }
          return currentUnits // No modificar el estado, solo leerlo
        })
      }, 500)
    }

    websocket.onclose = () => {
      console.log('✗ WebSocket desconectado')
      setWsConnected(false)
      setWs(null)

      // Reconectar después de 5 segundos
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Reintentando conexión...')
        setWs(null) // Esto disparará el useEffect nuevamente
      }, 5000)
    }

    websocket.onerror = (error) => {
      console.error('Error WebSocket:', error)
    }

    websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleWebSocketMessage(message)
      } catch (error) {
        console.error('Error procesando mensaje:', error)
      }
    }

    setWs(websocket)

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.close()
      }
    }
  }, [units, setWs, setWsConnected, ws, map, markersRef, setUnits, setEvents, handleWebSocketMessage])

  // Heartbeat
  useEffect(() => {
    if (!ws || !wsConnected) return

    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'PING' }))
      }
    }, 30000) // Cada 30 segundos

    return () => clearInterval(interval)
  }, [ws, wsConnected])
}
