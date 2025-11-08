const API_BASE = 'http://localhost:8000/api/v1'

export const loadUnits = async () => {
  try {
    const response = await fetch(`${API_BASE}/unidades?activo=true`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return await response.json()
  } catch (error) {
    console.error('Error cargando unidades:', error)
    return null
  }
}

export const loadEvents = async (filters = {}) => {
  try {
    const params = new URLSearchParams()
    
    if (filters.unidad_id) {
      params.append('unidad_id', filters.unidad_id)
    }
    if (filters.tipo) {
      params.append('tipo', filters.tipo)
    }
    params.append('limit', filters.limit || 20)

    const response = await fetch(`${API_BASE}/eventos?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return await response.json()
  } catch (error) {
    console.error('Error cargando eventos:', error)
    return []
  }
}

export const loadPOIs = async (categoria = null) => {
  try {
    const params = new URLSearchParams()
    if (categoria) {
      params.append('categoria', categoria)
    }

    const response = await fetch(`${API_BASE}/pois?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return await response.json()
  } catch (error) {
    console.error('Error cargando POIs:', error)
    return []
  }
}

