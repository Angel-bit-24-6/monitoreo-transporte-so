import { useState } from 'react'
import { useApp } from '../context/AppContext'

const Chatbot = () => {
  const { chatbot, setChatbot } = useApp()
  const [inputValue, setInputValue] = useState('')

  const handleToggle = () => {
    setChatbot({ ...chatbot, isOpen: !chatbot.isOpen })
  }

  const handleClose = () => {
    setChatbot({ ...chatbot, isOpen: false })
  }

  const handleSend = () => {
    if (!inputValue.trim()) return
    // TODO: Implementar envío de mensaje
    setInputValue('')
  }

  return (
    <>
      {/* Botón flotante del chatbot */}
      <button
        className={`chatbot-toggle fixed bottom-5 left-5 w-[60px] h-[60px] rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white border-none text-2xl cursor-pointer shadow-lg z-[1100] transition-all duration-300 flex items-center justify-center hover:scale-110 active:scale-95 ${
          chatbot.isOpen ? 'from-pink-500 to-red-500' : ''
        }`}
        onClick={handleToggle}
        aria-label="Abrir asistente"
      >
        💬
        {chatbot.unreadCount > 0 && (
          <span className="chatbot-badge absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shadow-md">
            {chatbot.unreadCount > 9 ? '9+' : chatbot.unreadCount}
          </span>
        )}
      </button>

      {/* Ventana del chatbot */}
      {chatbot.isOpen && (
        <div className="chatbot-window fixed bottom-24 left-5 w-[380px] h-[550px] bg-white rounded-xl shadow-2xl z-[1100] flex flex-col overflow-hidden">
          <div className="chatbot-header bg-gradient-to-r from-indigo-500 to-purple-600 text-white p-4 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/30 flex items-center justify-center text-xl">
                🤖
              </div>
              <div>
                <h3 className="m-0 text-lg font-semibold">Asistente Virtual</h3>
                <p className="m-0 text-xs opacity-90">En línea</p>
              </div>
            </div>
            <button
              className="bg-transparent border-none text-white text-xl cursor-pointer p-1 transition-opacity duration-200 hover:opacity-70"
              onClick={handleClose}
              aria-label="Cerrar chatbot"
            >
              ✕
            </button>
          </div>

          <div className="chatbot-messages flex-1 overflow-y-auto p-5 bg-gray-50 flex flex-col gap-3">
            {chatbot.messages.length === 0 && (
              <div className="text-center text-gray-400 text-sm">
                Escribe un mensaje para comenzar...
              </div>
            )}
            {/* Los mensajes se renderizarán aquí */}
          </div>

          <div className="chatbot-input-area p-4 bg-white border-t border-gray-200 flex-shrink-0 flex gap-2.5">
            <input
              type="text"
              className="chatbot-input flex-1 p-3 border-2 border-gray-200 rounded-full text-sm outline-none transition-colors duration-200 focus:border-indigo-500"
              placeholder="Escribe tu pregunta..."
              maxLength={500}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  handleSend()
                }
              }}
            />
            <button
              className="chatbot-send w-11 h-11 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white border-none text-xl cursor-pointer transition-all duration-200 flex items-center justify-center hover:scale-105 active:scale-95"
              onClick={handleSend}
              aria-label="Enviar mensaje"
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export default Chatbot

