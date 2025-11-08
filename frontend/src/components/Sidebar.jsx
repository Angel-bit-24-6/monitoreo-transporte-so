import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import UnitsList from './UnitsList'
import ConnectionStatus from './ConnectionStatus'

const Sidebar = ({ sidebarOpen, onClose }) => {
  const { wsConnected } = useApp()

  return (
    <div 
      className={`sidebar w-[350px] text-white flex flex-col overflow-hidden transition-all duration-500 ease-out md:translate-x-0 shadow-2xl bg-gradient-to-b from-slate-800 to-slate-900 backdrop-blur-md ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      } md:relative fixed top-0 left-0 h-full z-[1500]`}
      id="sidebar"
    >
      {/* Header con gradiente animado */}
      <div className="sidebar-header p-6 relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700 border-b-4 border-gradient-header">
        <div className="absolute inset-0 bg-gradient-to-r from-teal-500/10 via-cyan-500/10 to-blue-500/10 animate-pulse"></div>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="text-3xl animate-bounce">🚍</div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-teal-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent">
              Monitor de Transporte
            </h1>
          </div>
          <p className="text-sm text-gray-300 flex items-center gap-2">
            <span className="inline-block w-2 h-2 bg-teal-400 rounded-full animate-pulse"></span>
            Sistema de Seguimiento en Tiempo Real
          </p>
        </div>
      </div>

      <ConnectionStatus />

      <UnitsList onSelectUnit={onClose} />
    </div>
  )
}

export default Sidebar

