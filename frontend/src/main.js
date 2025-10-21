/**
 * Dashboard principal - Sistema de Monitoreo de Transporte
 */

const API_BASE = 'http://localhost:8000/api/v1';
const WS_URL = 'ws://localhost:8000/ws/dashboard';
const CHATBOT_WS_URL = 'ws://localhost:8000/ws/chatbot';

// Estado global
const state = {
    ws: null,
    map: null,
    markers: {},
    units: {},
    events: [],
    selectedUnit: null,
    filters: {
        unidad_id: '',
        tipo: '',
        limit: 20,
    },
    // Estado de POIs
    pois: [],
    poiMarkers: {},
    highlightedMarkers: [], // Marcadores resaltados por el chatbot
    poiFilters: {
        categoria: '', // '' = todas las categorías
        showPOIs: true // Mostrar/ocultar POIs en el mapa
    },
    // Estado del chatbot
    chatbot: {
        ws: null,
        isOpen: false,
        messages: [],
        unreadCount: 0,
    }
};

// Iconos personalizados para Leaflet
const createBusIcon = (isOnline) => {
    const color = isOnline ? '#2ecc71' : '#e74c3c';
    return L.divIcon({
        className: 'custom-bus-icon',
        html: `<div style="background-color: ${color}; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); font-size: 16px;">🚍</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
    });
};

// Inicializar mapa
function initMap() {
    // Centro en Tapachula, Chiapas, México
    state.map = L.map('map').setView([14.908598, -92.252354], 13);

    // Tile layer de OpenStreetMap (configuración original)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(state.map);

    console.log('✓ Mapa inicializado');
}

// Cargar unidades desde API
async function loadUnits() {
    try {
        const response = await fetch(`${API_BASE}/unidades?activo=true`);
        const units = await response.json();

        console.log(`✓ Cargadas ${units.length} unidades`);

        // Guardar en estado
        units.forEach(unit => {
            state.units[unit.id] = {
                ...unit,
                is_connected: false,
                last_position: null,
            };
        });

        // Renderizar lista
        renderUnitsList();

        // NO suscribirse aquí, se hará cuando el WebSocket esté conectado

    } catch (error) {
        console.error('Error cargando unidades:', error);
    }
}

// Renderizar lista de unidades en sidebar
function renderUnitsList() {
    const container = document.getElementById('units-list');
    const units = Object.values(state.units);

    if (units.length === 0) {
        container.innerHTML = '<div class="loading">No hay unidades disponibles</div>';
        return;
    }

    container.innerHTML = units.map(unit => {
        const statusClass = unit.is_connected ? 'online' : 'offline';
        const speed = unit.last_position?.speed
            ? `${(unit.last_position.speed * 3.6).toFixed(1)} km/h`
            : 'N/A';

        return `
            <div class="unit-item ${statusClass}" data-unit-id="${unit.id}" onclick="selectUnit('${unit.id}')">
                <div class="unit-header">
                    <span class="unit-id">${unit.id}</span>
                    <span class="unit-status ${statusClass}">
                        ${unit.is_connected ? 'En línea' : 'Offline'}
                    </span>
                </div>
                <div class="unit-info">
                    <div>🚗 ${unit.placa || 'Sin placa'}</div>
                    <div>👤 ${unit.chofer || 'Sin chofer'}</div>
                    <div class="unit-speed">⚡ ${speed}</div>
                </div>
            </div>
        `;
    }).join('');
}

// Seleccionar unidad
window.selectUnit = function(unidadId) {
    state.selectedUnit = unidadId;

    // Actualizar UI
    document.querySelectorAll('.unit-item').forEach(el => {
        el.classList.remove('active');
    });
    document.querySelector(`[data-unit-id="${unidadId}"]`)?.classList.add('active');

    // Centrar mapa en la unidad
    const unit = state.units[unidadId];
    if (unit?.last_position) {
        state.map.setView([unit.last_position.lat, unit.last_position.lon], 15);
    }
};

// Conectar WebSocket
function connectWebSocket() {
    console.log('Conectando WebSocket...');

    state.ws = new WebSocket(WS_URL);

    state.ws.onopen = () => {
        console.log('✓ WebSocket conectado');
        updateConnectionStatus(true);

        // Suscribirse a todas las unidades ahora que WebSocket está conectado
        const unidadIds = Object.keys(state.units);
        if (unidadIds.length > 0) {
            subscribeToUnits(unidadIds);
            console.log(`✓ Intentando suscribirse a ${unidadIds.length} unidades`);
        } else {
            console.log('⚠️ No hay unidades cargadas aún para suscribirse');
        }
    };

    state.ws.onclose = () => {
        console.log('✗ WebSocket desconectado');
        updateConnectionStatus(false);

        // Reconectar después de 5 segundos
        setTimeout(() => {
            console.log('Reintentando conexión...');
            connectWebSocket();
        }, 5000);
    };

    state.ws.onerror = (error) => {
        console.error('Error WebSocket:', error);
    };

    state.ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        } catch (error) {
            console.error('Error procesando mensaje:', error);
        }
    };
}

// Actualizar estado de conexión en UI
function updateConnectionStatus(connected) {
    const dot = document.getElementById('ws-status-dot');
    const text = document.getElementById('ws-status-text');

    if (connected) {
        dot.classList.add('connected');
        text.textContent = 'Conectado';
    } else {
        dot.classList.remove('connected');
        text.textContent = 'Desconectado';
    }
}

// Suscribirse a unidades
function subscribeToUnits(unidadIds) {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket no está conectado');
        return;
    }

    const message = {
        type: 'SUBSCRIBE',
        unidad_ids: unidadIds,
    };

    state.ws.send(JSON.stringify(message));
    console.log(`✓ Suscrito a ${unidadIds.length} unidades`);
}

// Manejar mensajes WebSocket
function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'POSITION_UPDATE':
            handlePositionUpdate(message);
            break;
        case 'EVENT_ALERT':
            handleEventAlert(message);
            break;
        case 'CONNECTION_STATE':
            handleConnectionState(message);
            break;
        case 'SUBSCRIBED':
            console.log(`✓ Confirmación de suscripción: ${message.message}`);
            break;
        case 'PONG':
            // Heartbeat response
            break;
        default:
            console.log('Mensaje desconocido:', message);
    }
}

// Actualizar posición de unidad
function handlePositionUpdate(data) {
    const { unidad_id, lat, lon, speed, heading, timestamp } = data;

    // Actualizar estado
    if (state.units[unidad_id]) {
        state.units[unidad_id].last_position = { lat, lon, speed, heading, timestamp };
    }

    // Actualizar o crear marcador
    if (state.markers[unidad_id]) {
        state.markers[unidad_id].setLatLng([lat, lon]);
    } else {
        const unit = state.units[unidad_id];
        const marker = L.marker([lat, lon], {
            icon: createBusIcon(unit?.is_connected),
        }).addTo(state.map);

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
        `;

        marker.bindPopup(popupContent);
        state.markers[unidad_id] = marker;
    }

    // Actualizar lista
    renderUnitsList();
}

// Manejar alerta de evento
function handleEventAlert(data) {
    const { unidad_id, event_tipo, detalle, timestamp, event_id } = data;

    console.log(`🚨 Evento: ${event_tipo} - ${unidad_id} (ID: ${event_id})`);

    // Verificar si coincide con los filtros actuales
    const passesFilter =
        (!state.filters.unidad_id || state.filters.unidad_id === unidad_id) &&
        (!state.filters.tipo || state.filters.tipo === event_tipo);

    if (passesFilter) {
        // Agregar a lista de eventos (solo si pasa los filtros)
        state.events.unshift({
            id: event_id,  // Guardar ID para evitar duplicados
            unidad_id,
            tipo: event_tipo,
            detalle,
            timestamp,
        });

        // Mantener límite de eventos según filtro
        if (state.events.length > state.filters.limit) {
            state.events = state.events.slice(0, state.filters.limit);
        }

        // Renderizar eventos
        renderEventsList();
        updateEventsCount();
    } else {
        console.log(`⚠️ Evento ignorado (no pasa los filtros)`);
    }

    // Mostrar notificación visual en el marcador (siempre, sin importar filtros)
    if (state.markers[unidad_id]) {
        state.markers[unidad_id].openPopup();
    }
}

// Manejar cambio de estado de conexión
function handleConnectionState(data) {
    const { unidad_id, is_connected } = data;

    if (state.units[unidad_id]) {
        state.units[unidad_id].is_connected = is_connected;

        // Actualizar icono del marcador
        if (state.markers[unidad_id]) {
            state.markers[unidad_id].setIcon(createBusIcon(is_connected));
        }

        // Actualizar lista
        renderUnitsList();
    }
}

// Renderizar lista de eventos
function renderEventsList() {
    const container = document.getElementById('events-list');

    if (state.events.length === 0) {
        container.innerHTML = '<div class="loading">Sin eventos</div>';
        return;
    }

    container.innerHTML = state.events.map(event => {
        const time = new Date(event.timestamp).toLocaleTimeString();
        const typeNames = {
            'OUT_OF_BOUND': '🚨 Fuera de Ruta',
            'STOP_LONG': '⏸️ Detención Prolongada',
            'SPEEDING': '⚡ Exceso de Velocidad',
            'GENERAL_ALERT': '⚠️ Alerta General',
        };

        return `
            <div class="event-item ${event.tipo}">
                <div class="event-time">${time} - ${event.unidad_id}</div>
                <div class="event-type">${typeNames[event.tipo] || event.tipo}</div>
                <div class="event-detail">${event.detalle}</div>
            </div>
        `;
    }).join('');
}

// Heartbeat para mantener conexión activa
function startHeartbeat() {
    setInterval(() => {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: 'PING' }));
        }
    }, 30000); // Cada 30 segundos
}

// ==================== NUEVAS FUNCIONES: Eventos Históricos y Filtros ====================

// Cargar eventos desde la API REST
async function loadRecentEvents() {
    try {
        // Construir URL con parámetros de filtro
        const params = new URLSearchParams();

        if (state.filters.unidad_id) {
            params.append('unidad_id', state.filters.unidad_id);
        }

        if (state.filters.tipo) {
            params.append('tipo', state.filters.tipo);
        }

        params.append('limit', state.filters.limit);

        const url = `${API_BASE}/eventos?${params.toString()}`;
        console.log('Cargando eventos desde:', url);

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const events = await response.json();

        console.log(`✓ Cargados ${events.length} eventos desde la base de datos`);

        // Reemplazar eventos actuales con los cargados
        state.events = events.map(event => ({
            unidad_id: event.unidad_id,
            tipo: event.tipo,
            detalle: event.detalle,
            timestamp: event.ts,
        }));

        // Renderizar eventos
        renderEventsList();
        updateEventsCount();

    } catch (error) {
        console.error('Error cargando eventos:', error);
        const container = document.getElementById('events-list');
        container.innerHTML = '<div class="loading" style="color: #e74c3c;">Error al cargar eventos</div>';
    }
}

// Poblar select de unidades
function populateUnitFilter() {
    const select = document.getElementById('filter-unit');

    // Limpiar opciones excepto la primera
    select.innerHTML = '<option value="">Todas las unidades</option>';

    // Agregar opciones de unidades
    Object.values(state.units).forEach(unit => {
        const option = document.createElement('option');
        option.value = unit.id;
        option.textContent = `${unit.id} - ${unit.placa || 'Sin placa'}`;
        select.appendChild(option);
    });
}

// Aplicar filtros
window.applyFilters = async function() {
    // Leer valores de los filtros
    state.filters.unidad_id = document.getElementById('filter-unit').value;
    state.filters.tipo = document.getElementById('filter-type').value;
    state.filters.limit = parseInt(document.getElementById('filter-limit').value);

    console.log('Aplicando filtros:', state.filters);

    // Recargar eventos con filtros
    await loadRecentEvents();
};

// Limpiar filtros
window.clearFilters = async function() {
    // Reset filtros
    state.filters.unidad_id = '';
    state.filters.tipo = '';
    state.filters.limit = 20;

    // Reset UI
    document.getElementById('filter-unit').value = '';
    document.getElementById('filter-type').value = '';
    document.getElementById('filter-limit').value = '20';

    console.log('Filtros limpiados');

    // Recargar eventos sin filtros
    await loadRecentEvents();
};

// Actualizar contador de eventos
function updateEventsCount() {
    const countElement = document.getElementById('events-count');
    const count = state.events.length;

    let filterText = '';
    if (state.filters.unidad_id) {
        filterText += ` · Unidad: ${state.filters.unidad_id}`;
    }
    if (state.filters.tipo) {
        const typeNames = {
            'OUT_OF_BOUND': 'Fuera de Ruta',
            'STOP_LONG': 'Detención Prolongada',
            'SPEEDING': 'Exceso de Velocidad',
            'GENERAL_ALERT': 'Alerta General',
        };
        filterText += ` · Tipo: ${typeNames[state.filters.tipo]}`;
    }

    countElement.textContent = `${count} eventos${filterText}`;
}

// ==================== RESPONSIVE: Menú Hamburguesa para Móviles ====================

function initMobileMenu() {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (!menuToggle || !sidebar || !overlay) {
        console.warn('Elementos del menú móvil no encontrados');
        return;
    }

    // Abrir/cerrar sidebar
    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('active');
    });

    // Cerrar sidebar al hacer click en el overlay
    overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
    });

    // Cerrar sidebar al seleccionar una unidad (en móviles)
    document.addEventListener('click', (e) => {
        if (e.target.closest('.unit-item') && window.innerWidth <= 767) {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }
    });

    // Cerrar sidebar al redimensionar a desktop
    window.addEventListener('resize', () => {
        if (window.innerWidth > 767) {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }
    });

    console.log('✓ Menú móvil inicializado');
}

// Colapsar/expandir panel de eventos (todas las pantallas)
function initEventsCollapse() {
    const eventsHeader = document.getElementById('events-header');
    const eventsPanel = document.getElementById('events-panel');

    if (!eventsHeader || !eventsPanel) {
        console.warn('Elementos del panel de eventos no encontrados');
        return;
    }

    eventsHeader.addEventListener('click', () => {
        // Permitir colapsar en todas las pantallas
        eventsPanel.classList.toggle('collapsed');
    });

    console.log('✓ Panel de eventos colapsable inicializado (todas las pantallas)');
}

// ==================== FUNCIONES DE POIs ====================

// Íconos para POIs según categoría
const POI_ICONS = {
    'hospital': '🏥',
    'farmacia': '💊',
    'papeleria': '📝',
    'gasolinera': '⛽',
    'banco': '🏦'
};

// Colores para POIs según categoría
const POI_COLORS = {
    'hospital': '#e74c3c',    // Rojo
    'farmacia': '#3498db',    // Azul
    'papeleria': '#f39c12',   // Naranja
    'gasolinera': '#9b59b6',  // Púrpura
    'banco': '#27ae60'        // Verde
};

// Crear ícono personalizado para POI
function createPOIIcon(categoria) {
    const emoji = POI_ICONS[categoria] || '📍';
    const color = POI_COLORS[categoria] || '#95a5a6';

    return L.divIcon({
        className: 'poi-icon',
        html: `<div style="background-color: ${color}; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); font-size: 18px;">${emoji}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16]
    });
}

// Cargar POIs desde la API
async function loadPOIs() {
    try {
        const params = new URLSearchParams();
        if (state.poiFilters.categoria) {
            params.append('categoria', state.poiFilters.categoria);
        }

        const url = `${API_BASE}/pois?${params.toString()}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        state.pois = await response.json();
        console.log(`✓ Cargados ${state.pois.length} POIs`);

        // Renderizar POIs en el mapa
        renderPOIs();

    } catch (error) {
        console.error('Error cargando POIs:', error);
    }
}

// Renderizar POIs en el mapa
function renderPOIs() {
    // Limpiar marcadores anteriores
    clearPOIMarkers();

    if (!state.poiFilters.showPOIs) {
        return; // No mostrar POIs si está desactivado
    }

    // Crear marcadores para cada POI
    state.pois.forEach(poi => {
        const marker = L.marker([poi.lat, poi.lon], {
            icon: createPOIIcon(poi.categoria)
        }).addTo(state.map);

        // Crear popup con información del POI
        const popupContent = `
            <div class="poi-popup">
                <div class="popup-header" style="background-color: ${POI_COLORS[poi.categoria] || '#95a5a6'}">
                    ${POI_ICONS[poi.categoria] || '📍'} ${poi.nombre}
                </div>
                <div class="popup-info">
                    <div><strong>Categoría:</strong> ${poi.categoria}</div>
                    ${poi.direccion ? `<div><strong>Dirección:</strong> ${poi.direccion}</div>` : ''}
                    ${poi.telefono ? `<div><strong>Teléfono:</strong> ${poi.telefono}</div>` : ''}
                    ${poi.horario ? `<div><strong>Horario:</strong> ${poi.horario}</div>` : ''}
                </div>
            </div>
        `;

        marker.bindPopup(popupContent);
        state.poiMarkers[poi.id] = marker;
    });

    console.log(`✓ Renderizados ${Object.keys(state.poiMarkers).length} POIs en el mapa`);
}

// Limpiar marcadores de POIs del mapa
function clearPOIMarkers() {
    Object.values(state.poiMarkers).forEach(marker => {
        state.map.removeLayer(marker);
    });
    state.poiMarkers = {};
}

// Buscar POI por nombre
async function searchPOI(query) {
    if (!query || query.length < 2) {
        return [];
    }

    try {
        const params = new URLSearchParams({
            q: query,
            limit: 10
        });

        if (state.poiFilters.categoria) {
            params.append('categoria', state.poiFilters.categoria);
        }

        const url = `${API_BASE}/pois/buscar?${params.toString()}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const results = await response.json();
        console.log(`✓ Encontrados ${results.length} POIs para "${query}"`);
        return results;

    } catch (error) {
        console.error('Error buscando POIs:', error);
        return [];
    }
}

// Buscar POIs cercanos a una coordenada
async function searchNearbyPOIs(lat, lon, categoria = null, radio = 1000) {
    try {
        const params = new URLSearchParams({
            lat: lat,
            lon: lon,
            radio: radio,
            limit: 10
        });

        if (categoria) {
            params.append('categoria', categoria);
        }

        const url = `${API_BASE}/pois/cercanos?${params.toString()}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const results = await response.json();
        console.log(`✓ Encontrados ${results.length} POIs cercanos`);
        return results;

    } catch (error) {
        console.error('Error buscando POIs cercanos:', error);
        return [];
    }
}

// Filtrar POIs por categoría
window.filterPOIsByCategory = async function(categoria) {
    state.poiFilters.categoria = categoria;
    await loadPOIs();
};

// Mostrar/ocultar POIs en el mapa
window.togglePOIs = function() {
    state.poiFilters.showPOIs = !state.poiFilters.showPOIs;
    renderPOIs();
};

// Inicialización
async function init() {
    console.log('=== Inicializando Dashboard ===');

    initMap();
    await loadUnits();

    // Poblar filtro de unidades
    populateUnitFilter();

    // Cargar eventos históricos desde la base de datos
    await loadRecentEvents();

    // Cargar POIs en el mapa
    await loadPOIs();

    connectWebSocket();
    startHeartbeat();

    // Inicializar funcionalidades responsive
    initMobileMenu();
    initEventsCollapse();

    // Inicializar chatbot
    initChatbot();

    console.log('✓ Dashboard listo');
}

// ==================== CHATBOT ====================

/**
 * Inicializar chatbot
 */
function initChatbot() {
    const toggleBtn = document.getElementById('chatbot-toggle');
    const closeBtn = document.getElementById('chatbot-close');
    const chatWindow = document.getElementById('chatbot-window');
    const inputField = document.getElementById('chatbot-input');
    const sendBtn = document.getElementById('chatbot-send');

    if (!toggleBtn || !closeBtn || !chatWindow || !inputField || !sendBtn) {
        console.warn('Elementos del chatbot no encontrados');
        return;
    }

    // Toggle chatbot window
    toggleBtn.addEventListener('click', () => {
        state.chatbot.isOpen = !state.chatbot.isOpen;

        if (state.chatbot.isOpen) {
            chatWindow.classList.add('open');
            toggleBtn.classList.add('open');

            // Resetear contador de mensajes no leídos
            state.chatbot.unreadCount = 0;
            updateChatbotBadge();

            // Conectar WebSocket si no está conectado
            if (!state.chatbot.ws || state.chatbot.ws.readyState !== WebSocket.OPEN) {
                connectChatbotWebSocket();
            }

            // Focus en input
            setTimeout(() => inputField.focus(), 300);
        } else {
            chatWindow.classList.remove('open');
            toggleBtn.classList.remove('open');
        }
    });

    // Cerrar chatbot
    closeBtn.addEventListener('click', () => {
        state.chatbot.isOpen = false;
        chatWindow.classList.remove('open');
        toggleBtn.classList.remove('open');
    });

    // Enviar mensaje con Enter
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatbotMessage();
        }
    });

    // Enviar mensaje con botón
    sendBtn.addEventListener('click', () => {
        sendChatbotMessage();
    });

    console.log('✓ Chatbot inicializado');
}

/**
 * Conectar WebSocket del chatbot
 */
function connectChatbotWebSocket() {
    console.log('Conectando chatbot WebSocket...');

    state.chatbot.ws = new WebSocket(CHATBOT_WS_URL);

    state.chatbot.ws.onopen = () => {
        console.log('✓ Chatbot WebSocket conectado');
        updateChatbotStatus('En línea');
    };

    state.chatbot.ws.onclose = () => {
        console.log('✗ Chatbot WebSocket desconectado');
        updateChatbotStatus('Desconectado');

        // Reconectar después de 5 segundos si el chatbot está abierto
        if (state.chatbot.isOpen) {
            setTimeout(() => {
                console.log('Reintentando conexión chatbot...');
                connectChatbotWebSocket();
            }, 5000);
        }
    };

    state.chatbot.ws.onerror = (error) => {
        console.error('Error chatbot WebSocket:', error);
        updateChatbotStatus('Error');
    };

    state.chatbot.ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleChatbotMessage(message);
        } catch (error) {
            console.error('Error procesando mensaje chatbot:', error);
        }
    };
}

/**
 * Actualizar estado de conexión del chatbot
 */
function updateChatbotStatus(status) {
    const statusElement = document.getElementById('chatbot-status');
    if (statusElement) {
        statusElement.textContent = status;
    }
}

/**
 * Manejar mensajes del chatbot
 */
function handleChatbotMessage(message) {
    const { type, message: text, timestamp, data } = message;

    if (type === 'BOT_MESSAGE') {
        // Ocultar indicador de escritura
        hideTypingIndicator();

        // Agregar mensaje del bot
        addChatMessage(text, 'bot', timestamp);

        // Manejar acciones de mapa
        if (data && data.action === 'highlight_pois') {
            highlightPOIsOnMap(data.pois, data.zoom_to_fit);
        }

        // Si el chatbot está cerrado, incrementar contador
        if (!state.chatbot.isOpen) {
            state.chatbot.unreadCount++;
            updateChatbotBadge();
        }
    } else if (type === 'PONG') {
        // Heartbeat response
    }
}

/**
 * Enviar mensaje del usuario
 */
function sendChatbotMessage() {
    const inputField = document.getElementById('chatbot-input');
    const sendBtn = document.getElementById('chatbot-send');
    const text = inputField.value.trim();

    if (!text) return;

    if (!state.chatbot.ws || state.chatbot.ws.readyState !== WebSocket.OPEN) {
        console.error('Chatbot WebSocket no está conectado');
        return;
    }

    // Agregar mensaje del usuario a la UI
    addChatMessage(text, 'user');

    // Enviar mensaje al servidor
    state.chatbot.ws.send(JSON.stringify({
        type: 'USER_MESSAGE',
        message: text
    }));

    // Limpiar input
    inputField.value = '';

    // Mostrar indicador de escritura
    showTypingIndicator();

    // Deshabilitar botón temporalmente
    sendBtn.disabled = true;
    setTimeout(() => {
        sendBtn.disabled = false;
    }, 500);
}

/**
 * Enviar mensaje rápido (sugerencias)
 */
window.sendQuickMessage = function(text) {
    const inputField = document.getElementById('chatbot-input');
    inputField.value = text;
    sendChatbotMessage();
};

/**
 * Agregar mensaje a la UI
 */
function addChatMessage(text, sender, timestamp = null) {
    const messagesContainer = document.getElementById('chatbot-messages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    // Convertir texto con markdown simple (negrita)
    const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convertir saltos de línea a <br>
    const htmlText = formattedText.replace(/\n/g, '<br>');

    messageDiv.innerHTML = htmlText;

    // Agregar timestamp si es del bot
    if (sender === 'bot' && timestamp) {
        const time = new Date(timestamp).toLocaleTimeString();
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = time;
        messageDiv.appendChild(timeDiv);
    }

    messagesContainer.appendChild(messageDiv);

    // Scroll al último mensaje
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Guardar en estado
    state.chatbot.messages.push({ text, sender, timestamp });
}

/**
 * Mostrar indicador de escritura
 */
function showTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.classList.add('active');

        // Scroll al indicador
        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

/**
 * Ocultar indicador de escritura
 */
function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.classList.remove('active');
    }
}

/**
 * Actualizar badge de mensajes no leídos
 */
function updateChatbotBadge() {
    const badge = document.getElementById('chatbot-badge');
    if (badge) {
        if (state.chatbot.unreadCount > 0) {
            badge.textContent = state.chatbot.unreadCount > 9 ? '9+' : state.chatbot.unreadCount;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

/**
 * Resaltar POIs en el mapa con animaciones
 * @param {Array} pois - Array de POIs a resaltar
 * @param {Boolean} zoomToFit - Si debe hacer zoom para ajustar todos los POIs
 */
function highlightPOIsOnMap(pois, zoomToFit = true) {
    // Limpiar resaltados anteriores
    clearHighlightedPOIs();

    if (!pois || pois.length === 0) {
        console.log('No hay POIs para resaltar');
        return;
    }

    console.log(`Resaltando ${pois.length} POIs en el mapa`);

    const bounds = L.latLngBounds();
    let highlightedCount = 0;

    pois.forEach(poi => {
        // Crear marcador resaltado con animación
        const icon = createHighlightedPOIIcon(poi.categoria);

        const marker = L.marker([poi.lat, poi.lon], {
            icon: icon,
            zIndexOffset: 1000 // Asegurar que esté encima de otros marcadores
        }).addTo(state.map);

        // Agregar clase para animación CSS
        const iconElement = marker.getElement();
        if (iconElement) {
            iconElement.classList.add('highlighted-marker');
            iconElement.classList.add('poi-marker-highlighted');
        }

        // Crear popup mejorado
        const popupContent = `
            <div class="poi-popup poi-popup-highlighted">
                <div class="popup-header" style="background-color: ${POI_COLORS[poi.categoria] || '#95a5a6'}">
                    ${POI_ICONS[poi.categoria] || '📍'} ${poi.nombre}
                </div>
                <div class="popup-info">
                    <div><strong>Categoría:</strong> ${poi.categoria}</div>
                    ${poi.direccion ? `<div><strong>Dirección:</strong> ${poi.direccion}</div>` : ''}
                    ${poi.telefono ? `<div><strong>Teléfono:</strong> ${poi.telefono}</div>` : ''}
                    ${poi.horario ? `<div><strong>Horario:</strong> ${poi.horario}</div>` : ''}
                    ${poi.distancia ? `<div><strong>Distancia:</strong> ${(poi.distancia / 1000).toFixed(2)} km</div>` : ''}
                </div>
                <div class="popup-footer">
                    <small>📍 Resaltado por el asistente</small>
                </div>
            </div>
        `;

        marker.bindPopup(popupContent);

        // Guardar marcador en estado
        state.highlightedMarkers.push(marker);

        // Agregar coordenadas a bounds
        bounds.extend([poi.lat, poi.lon]);
        highlightedCount++;
    });

    console.log(`✓ ${highlightedCount} POIs resaltados en el mapa`);

    // Si solo hay un POI, abrir su popup automáticamente
    if (pois.length === 1 && state.highlightedMarkers.length > 0) {
        state.highlightedMarkers[0].openPopup();
    }

    // Hacer zoom para ajustar todos los POIs resaltados
    if (zoomToFit && state.highlightedMarkers.length > 0) {
        if (pois.length === 1) {
            // Para un solo POI, centrar con zoom específico
            state.map.setView([pois[0].lat, pois[0].lon], 16);
        } else {
            // Para múltiples POIs, ajustar bounds con padding
            state.map.fitBounds(bounds, {
                padding: [50, 50],
                maxZoom: 15
            });
        }
    }

    // Remover animación después de 4.5 segundos (3 pulsos de 1.5s)
    setTimeout(() => {
        state.highlightedMarkers.forEach(marker => {
            const iconElement = marker.getElement();
            if (iconElement) {
                iconElement.classList.remove('highlighted-marker');
            }
        });
    }, 4500);
}

/**
 * Limpiar POIs resaltados del mapa
 */
function clearHighlightedPOIs() {
    state.highlightedMarkers.forEach(marker => {
        state.map.removeLayer(marker);
    });
    state.highlightedMarkers = [];
    console.log('Resaltados limpiados');
}

/**
 * Crear ícono resaltado para POI
 */
function createHighlightedPOIIcon(categoria) {
    const emoji = POI_ICONS[categoria] || '📍';
    const color = POI_COLORS[categoria] || '#95a5a6';

    return L.divIcon({
        className: 'poi-icon poi-icon-highlighted',
        html: `<div style="
            background-color: ${color};
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 3px solid #FFD700;
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.8), 0 4px 10px rgba(0,0,0,0.4);
            font-size: 22px;
            position: relative;
        ">${emoji}</div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
        popupAnchor: [0, -20]
    });
}

/**
 * Función global para limpiar marcadores resaltados manualmente
 * Llamada desde el botón "Limpiar mapa" en el chatbot
 */
window.clearMapHighlights = function() {
    clearHighlightedPOIs();
    console.log('✓ Marcadores resaltados limpiados manualmente');
};

// Ejecutar al cargar página
init();
