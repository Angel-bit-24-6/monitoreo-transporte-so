import { useEffect, useRef } from 'react'
import { useApp } from '../context/AppContext'

export const useLeaflet = (mapElementRef) => {
  const { map, setMap } = useApp()
  const initializedRef = useRef(false)

  useEffect(() => {
    // Si ya está inicializado o ya hay un mapa, no hacer nada
    if (initializedRef.current || map) return

    // Función para inicializar el mapa (exactamente como en main.js)
    const initMap = () => {
      // Verificar que Leaflet esté disponible
      if (typeof L === 'undefined') {
        console.warn('Leaflet no está disponible aún, reintentando...')
        setTimeout(initMap, 100)
        return
      }

      // Buscar el elemento del mapa por ID (igual que en main.js)
      const mapElement = document.getElementById('map')
      if (!mapElement) {
        console.warn('Div del mapa no encontrado, reintentando...')
        setTimeout(initMap, 100)
        return
      }

      // Verificar que el div tenga dimensiones
      if (mapElement.offsetWidth === 0 || mapElement.offsetHeight === 0) {
        console.warn(`Div del mapa no tiene dimensiones (${mapElement.offsetWidth}x${mapElement.offsetHeight}), reintentando...`)
        setTimeout(initMap, 100)
        return
      }

      // Si ya hay un mapa en este elemento, no crear otro
      if (mapElement._leaflet_id) {
        console.warn('El mapa ya está inicializado en este elemento')
        return
      }

      try {
        // Inicializar mapa exactamente como en main.js
        // Centro en Tapachula, Chiapas, México
        const leafletMap = L.map('map').setView([14.908598, -92.252354], 13)

        // Tile layer de OpenStreetMap (configuración original)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          maxZoom: 19,
        }).addTo(leafletMap)

        setMap(leafletMap)
        initializedRef.current = true
        console.log('✓ Mapa inicializado')

        // Invalidar tamaño después de un pequeño delay para asegurar que se renderice correctamente
        setTimeout(() => {
          if (leafletMap) {
            leafletMap.invalidateSize()
          }
        }, 200)
      } catch (error) {
        console.error('Error inicializando mapa:', error)
      }
    }

    // Intentar inicializar inmediatamente
    initMap()

    return () => {
      if (map) {
        map.remove()
        initializedRef.current = false
      }
    }
  }, [map, setMap])

  return null
}
