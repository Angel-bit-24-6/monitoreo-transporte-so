import { createContext, useContext, useState, useEffect, useRef } from 'react'

const AppContext = createContext()

export const useApp = () => {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}

export const AppProvider = ({ children }) => {
  // Estado del mapa
  const [map, setMap] = useState(null)
  const markersRef = useRef({})
  const poiMarkersRef = useRef({})
  const highlightedMarkersRef = useRef([])

  // Estado de unidades
  const [units, setUnits] = useState({})
  const [selectedUnit, setSelectedUnit] = useState(null)

  // Estado de eventos
  const [events, setEvents] = useState([])
  const [filters, setFilters] = useState({
    unidad_id: '',
    tipo: '',
    limit: 20,
  })

  // Estado de POIs
  const [pois, setPois] = useState([])
  const [poiFilters, setPoiFilters] = useState({
    categoria: '',
    showPOIs: true,
  })

  // Estado de WebSocket
  const [ws, setWs] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)

  // Estado del chatbot
  const [chatbot, setChatbot] = useState({
    ws: null,
    isOpen: false,
    messages: [],
    unreadCount: 0,
  })

  // API Base URL
  const API_BASE = 'http://localhost:8000/api/v1'
  const WS_URL = 'ws://localhost:8000/ws/dashboard'
  const CHATBOT_WS_URL = 'ws://localhost:8000/ws/chatbot'

  const value = {
    // Mapa
    map,
    setMap,
    markersRef,
    poiMarkersRef,
    highlightedMarkersRef,

    // Unidades
    units,
    setUnits,
    selectedUnit,
    setSelectedUnit,

    // Eventos
    events,
    setEvents,
    filters,
    setFilters,

    // POIs
    pois,
    setPois,
    poiFilters,
    setPoiFilters,

    // WebSocket
    ws,
    setWs,
    wsConnected,
    setWsConnected,

    // Chatbot
    chatbot,
    setChatbot,

    // URLs
    API_BASE,
    WS_URL,
    CHATBOT_WS_URL,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

