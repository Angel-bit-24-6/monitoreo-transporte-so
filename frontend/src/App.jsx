import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import MapContainer from './components/MapContainer'
import EventsPanel from './components/EventsPanel'
import Chatbot from './components/Chatbot'
import WebSocketMonitor from './components/WebSocketMonitor'
import { AppProvider } from './context/AppContext'
import './input.css'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Inicializar menú móvil
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 767) {
        setSidebarOpen(false)
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const closeSidebar = () => {
    setSidebarOpen(false)
  }

  return (
    <AppProvider>
      <div 
        className="flex h-screen overflow-hidden relative" 
        style={{ 
          height: '100vh', 
          width: '100vw',
          display: 'flex',
          flexDirection: 'row',
          position: 'relative'
        }}
      >
        {/* Botón de menú hamburguesa (solo visible en móviles) */}
        <button 
          className="menu-toggle md:hidden"
          id="menu-toggle"
          aria-label="Toggle menu"
          onClick={toggleSidebar}
        >
          ☰
        </button>

        {/* Overlay oscuro para cerrar sidebar en móviles */}
        <div 
          className={`sidebar-overlay ${sidebarOpen ? 'active' : ''}`}
          id="sidebar-overlay"
          onClick={closeSidebar}
        />

        <Sidebar sidebarOpen={sidebarOpen} onClose={closeSidebar} />
        <MapContainer>
          <EventsPanel />
        </MapContainer>
        <Chatbot />
        <WebSocketMonitor />
      </div>
    </AppProvider>
  )
}

export default App

