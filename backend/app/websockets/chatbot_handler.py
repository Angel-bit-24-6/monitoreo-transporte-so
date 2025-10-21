"""
WebSocket handler para el chatbot de asistencia.
Procesa consultas de usuarios sobre POIs, rutas, y sistema.
"""
import re
import structlog
from typing import Optional, Dict, List
from fastapi import WebSocket
from datetime import datetime
import json

from ..core.database import db

logger = structlog.get_logger()


class ChatbotIntentProcessor:
    """
    Procesador de intenciones para el chatbot.
    Usa sistema de scoring con keywords para mayor flexibilidad.
    """

    def __init__(self):
        # Keywords para cada categoría
        self.categorias_keywords = {
            "hospital": ["hospital", "hospitales", "clínica", "clinica", "clínicas", "clinicas"],
            "farmacia": ["farmacia", "farmacias", "botica", "boticas"],
            "papeleria": ["papelería", "papeleria", "papelerías", "papelerias"],
            "gasolinera": ["gasolinera", "gasolineras", "gas", "combustible"],
            "banco": ["banco", "bancos", "cajero", "cajeros", "atm"]
        }

        # Keywords para detectar intenciones
        self.keywords_buscar_cercanos = ["cerca", "cercano", "cercana", "cercanos", "cercanas", "próximo", "próxima", "próximos", "próximas", "por aquí", "por acá"]
        self.keywords_listar = ["lista", "muestra", "muéstrame", "dame", "dime", "enumera", "todos", "todas", "cuántos", "cuantos", "cuántas", "cuantas", "disponibles"]
        self.keywords_buscar_nombre = ["busca", "buscar", "encuentra", "encontrar", "dónde está", "donde esta", "dónde queda", "donde queda"]

        # Patrones para detectar intenciones (orden importa: más específicos primero)
        self.intent_patterns = [
            # Búsqueda de POIs cercanos - MEJORADO
            {
                "name": "buscar_pois_cercanos",
                "patterns": [
                    # Patrón principal: busca/encuentra + categoria + cerca/cercano/próximo
                    r"(?:busca|encuentra|buscar|encontrar|hay|necesito|quiero)\s+(?:un|una|algún|alguna)?\s*(?:los|las)?\s*(hospital|hospitales|farmacia|farmacias|papelería|papeleria|papelerías|papelerias|gasolinera|gasolineras|banco|bancos|cajero|cajeros)\s+(?:cercano|cercana|cercanos|cercanas|cerca|próximo|próxima|próximos|próximas|por\s+aquí|por\s+aca)",
                    # Categoría + cerca/cercano/próximo
                    r"(hospital|hospitales|farmacia|farmacias|papelería|papeleria|papelerías|papelerias|gasolinera|gasolineras|banco|bancos|cajero|cajeros)\s+(?:cercano|cercana|cercanos|cercanas|cerca|próximo|próxima|próximos|próximas|por\s+aquí|por\s+aca)",
                    # Dónde hay + categoría
                    r"(?:dónde|donde|en\s+dónde|en\s+donde)\s+(?:hay|puedo\s+encontrar|está|esta|queda)\s+(?:un|una|algún|alguna)?\s*(?:los|las)?\s*(hospital|hospitales|farmacia|farmacias|papelería|papeleria|papelerías|papelerias|gasolinera|gasolineras|banco|bancos|cajero|cajeros)",
                ],
                "extract": ["categoria"]
            },
            # Listar POIs de una categoría - MEJORADO (debe ir ANTES de buscar_poi_nombre)
            {
                "name": "listar_pois_categoria",
                "patterns": [
                    # Lista/muestra + categoría
                    r"(?:lista|muestra|muéstrame|dame|dime|enumera|ver)\s+(?:todos|todas|los|las)?\s*(?:los|las)?\s*(hospital|hospitales|farmacia|farmacias|papelería|papeleria|papelerías|papelerias|gasolinera|gasolineras|banco|bancos|cajero|cajeros)",
                    # Categoría + disponibles/que hay
                    r"(hospital|hospitales|farmacia|farmacias|papelería|papeleria|papelerías|papelerias|gasolinera|gasolineras|banco|bancos|cajero|cajeros)\s+(?:disponibles|que\s+hay|existentes)",
                    # Cuántos + categoría
                    r"(?:cuántos|cuantos|cuántas|cuantas)\s+(hospital|hospitales|farmacia|farmacias|papelería|papeleria|papelerías|papelerias|gasolinera|gasolineras|banco|bancos|cajero|cajeros)",
                    # Palabra sola: Hospital, Farmacia, etc. (DEBE IR AL FINAL)
                    r"^(hospital|hospitales|farmacia|farmacias|papelería|papeleria|papelerías|papelerias|gasolinera|gasolineras|banco|bancos|cajero|cajeros)$",
                ],
                "extract": ["categoria"]
            },
            # Búsqueda de POI específico por nombre
            {
                "name": "buscar_poi_nombre",
                "patterns": [
                    r"(?:dónde|donde)\s+(?:está|esta|queda|se\s+encuentra)\s+(?:el|la)?\s*(.+)",
                    r"(?:busca|encuentra|buscar|encontrar)\s+(?:el|la)?\s*([A-ZÁÉÍÓÚÑ].+)",
                ],
                "extract": ["nombre"]
            },
            # Listar todas las categorías
            {
                "name": "listar_categorias",
                "patterns": [
                    r"(?:qué|que)\s+(?:tipo|tipos|categorías|categorias)\s+(?:de\s+)?(?:pois?|lugares|sitios|servicios)",
                    r"(?:qué|que)\s+(?:categorías|categorias)\s+(?:hay|existen|tienes|tienes\s+disponibles)",
                    r"(?:muestra|lista|cuáles|cuales)\s+(?:categorías|categorias|tipos)",
                    r"(?:opciones|servicios)\s+disponibles",
                ],
                "extract": []
            },
            # Ayuda general
            {
                "name": "ayuda",
                "patterns": [
                    r"(?:ayuda|help|qué\s+puedes\s+hacer|que\s+puedes\s+hacer|cómo\s+funciona|como\s+funciona)",
                    r"(?:opciones|comandos|qué\s+puedo\s+preguntar|que\s+puedo\s+preguntar)",
                ],
                "extract": []
            },
            # Saludo
            {
                "name": "saludo",
                "patterns": [
                    r"^(?:hola|hey|buenos\s+días|buenos\s+dias|buenas\s+tardes|buenas\s+noches|saludos)$",
                ],
                "extract": []
            },
            # Despedida
            {
                "name": "despedida",
                "patterns": [
                    r"(?:adiós|adios|chao|hasta\s+luego|gracias|bye|nos\s+vemos)",
                ],
                "extract": []
            },
        ]

        # Mapeo de categorías (normalización)
        self.categoria_map = {
            "hospital": "hospital",
            "hospitales": "hospital",
            "clínica": "hospital",
            "clinica": "hospital",
            "farmacia": "farmacia",
            "farmacias": "farmacia",
            "botica": "farmacia",
            "papelería": "papeleria",
            "papeleria": "papeleria",
            "papelerías": "papeleria",
            "papelerias": "papeleria",
            "gasolinera": "gasolinera",
            "gasolineras": "gasolinera",
            "gas": "gasolinera",
            "banco": "banco",
            "bancos": "banco",
            "cajero": "banco",
            "cajeros": "banco",
            "atm": "banco",
        }

    def detect_intent(self, message: str) -> Optional[Dict]:
        """
        Detecta la intención del mensaje del usuario usando sistema de scoring.
        Retorna dict con: {name, params} o None si no se detecta.
        """
        message_clean = message.strip()
        message_lower = message_clean.lower()

        # 1. Detectar si es saludo/despedida/ayuda (alta prioridad)
        for intent in self.intent_patterns:
            if intent["name"] in ["saludo", "despedida", "ayuda", "listar_categorias"]:
                for pattern in intent["patterns"]:
                    if re.search(pattern, message_lower):
                        logger.info("intent_detected", intent=intent["name"], message=message_clean)
                        return {"name": intent["name"], "params": {}}

        # 2. Detectar categoría mencionada
        categoria_detectada = None
        for cat, keywords in self.categorias_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    categoria_detectada = cat
                    break
            if categoria_detectada:
                break

        # 3. Calcular scores para diferentes intenciones
        scores = {
            "buscar_pois_cercanos": 0,
            "listar_pois_categoria": 0,
            "buscar_poi_nombre": 0
        }

        # Score para buscar cercanos
        for keyword in self.keywords_buscar_cercanos:
            if keyword in message_lower:
                scores["buscar_pois_cercanos"] += 10

        # Score para listar
        for keyword in self.keywords_listar:
            if keyword in message_lower:
                scores["listar_pois_categoria"] += 10

        # Score para buscar por nombre
        for keyword in self.keywords_buscar_nombre:
            if keyword in message_lower:
                scores["buscar_poi_nombre"] += 5

        # Si hay categoría detectada, aumentar score de cercanos y listar
        if categoria_detectada:
            scores["buscar_pois_cercanos"] += 3
            scores["listar_pois_categoria"] += 3

        # Si es solo una palabra (categoría sola), priorizar listar
        palabras = message_lower.split()
        if len(palabras) == 1 and categoria_detectada:
            scores["listar_pois_categoria"] += 20

        # 4. Determinar intención ganadora
        max_score = max(scores.values())

        if max_score == 0:
            # No se detectó ninguna intención clara
            logger.info("intent_not_detected", message=message_clean, scores=scores)
            return None

        intent_name = max(scores, key=scores.get)

        # 5. Extraer parámetros según la intención
        params = {}

        if intent_name in ["buscar_pois_cercanos", "listar_pois_categoria"]:
            if categoria_detectada:
                params["categoria"] = categoria_detectada
            else:
                # Intención sin categoría, no es válida
                logger.info("intent_without_category", intent=intent_name, message=message_clean)
                return None

        elif intent_name == "buscar_poi_nombre":
            # Extraer nombre después de keyword
            nombre = self._extract_nombre(message_clean, message_lower)
            if nombre:
                params["nombre"] = nombre
            else:
                # No se pudo extraer nombre
                logger.info("intent_without_name", message=message_clean)
                return None

        logger.info(
            "intent_detected",
            intent=intent_name,
            params=params,
            message=message_clean,
            scores=scores
        )

        return {
            "name": intent_name,
            "params": params
        }

    def _extract_nombre(self, message_original: str, message_lower: str) -> Optional[str]:
        """
        Extrae el nombre del lugar a buscar.
        """
        # Buscar después de keywords de búsqueda
        patterns = [
            r"(?:busca|buscar)\s+(?:el|la)?\s*(.+)",
            r"(?:encuentra|encontrar)\s+(?:el|la)?\s*(.+)",
            r"(?:dónde|donde)\s+(?:está|esta|queda|se encuentra)\s+(?:el|la)?\s*(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()

                # Remover palabras de contexto al final
                palabras_remover = ["cerca", "cercano", "cercana", "por favor", "porfavor"]
                for palabra in palabras_remover:
                    if nombre.endswith(palabra):
                        nombre = nombre[:-len(palabra)].strip()

                # Verificar que no sea una categoría sola
                for cat_keywords in self.categorias_keywords.values():
                    if nombre.lower() in cat_keywords:
                        return None

                return nombre

        return None


class ChatbotWebSocketHandler:
    """
    Handler WebSocket para el chatbot de asistencia.
    """

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = None
        self.intent_processor = ChatbotIntentProcessor()

    async def handle(self):
        """Manejar conexión WebSocket del chatbot"""
        try:
            await self.websocket.accept()
            self.session_id = f"chatbot-{datetime.utcnow().timestamp()}"

            logger.info("chatbot_connected", session_id=self.session_id)

            # Mensaje de bienvenida
            await self.send_message(
                "¡Hola! 👋 Soy tu asistente virtual. Puedo ayudarte a encontrar lugares en Tapachula.\n\n"
                "**Ejemplos de búsqueda:**\n"
                "• \"Hospitales cercanos\"\n"
                "• \"Farmacias cerca\"\n"
                "• \"Lista los bancos\"\n"
                "• \"Gasolinera\"\n"
                "• \"¿Dónde está Hospital General?\"\n"
                "• \"¿Qué categorías hay?\"\n\n"
                "Escribe \"ayuda\" para más información."
            )

            # Loop de mensajes
            while True:
                data = await self.websocket.receive_json()
                await self.process_message(data)

        except Exception as e:
            logger.error("chatbot_error", session_id=self.session_id, error=str(e))
        finally:
            logger.info("chatbot_disconnected", session_id=self.session_id)

    async def process_message(self, data: dict):
        """Procesar mensaje del usuario"""
        message_type = data.get("type")
        message_text = data.get("message", "").strip()

        if message_type == "USER_MESSAGE":
            if not message_text:
                await self.send_message("Por favor escribe un mensaje.")
                return

            # Detectar intención
            intent = self.intent_processor.detect_intent(message_text)

            if intent:
                await self.handle_intent(intent)
            else:
                # No se entendió la intención
                await self.send_message(
                    "Lo siento, no entendí tu pregunta. 🤔\n\n"
                    "Puedes preguntarme sobre:\n"
                    "• Hospitales, farmacias, papelerías, gasolineras, bancos\n"
                    "• Ubicaciones específicas\n"
                    "• Categorías disponibles\n\n"
                    "Escribe \"ayuda\" para ver ejemplos."
                )

        elif message_type == "PING":
            await self.websocket.send_json({"type": "PONG"})

    async def handle_intent(self, intent: dict):
        """Manejar una intención detectada"""
        intent_name = intent["name"]
        params = intent["params"]

        handlers = {
            "saludo": self.handle_saludo,
            "despedida": self.handle_despedida,
            "ayuda": self.handle_ayuda,
            "listar_categorias": self.handle_listar_categorias,
            "listar_pois_categoria": self.handle_listar_pois_categoria,
            "buscar_pois_cercanos": self.handle_buscar_cercanos,
            "buscar_poi_nombre": self.handle_buscar_nombre,
        }

        handler = handlers.get(intent_name)
        if handler:
            await handler(params)
        else:
            await self.send_message("Lo siento, no pude procesar tu solicitud.")

    async def handle_saludo(self, params: dict):
        """Responder a saludos"""
        await self.send_message(
            "¡Hola! 😊 ¿En qué puedo ayudarte hoy?\n\n"
            "Puedo ayudarte a encontrar:\n"
            "• 🏥 Hospitales\n"
            "• 💊 Farmacias\n"
            "• 📝 Papelerías\n"
            "• ⛽ Gasolineras\n"
            "• 🏦 Bancos\n\n"
            "Solo pregúntame lo que necesites."
        )

    async def handle_despedida(self, params: dict):
        """Responder a despedidas"""
        await self.send_message(
            "¡Hasta pronto! 👋 Si necesitas ayuda nuevamente, aquí estaré."
        )

    async def handle_ayuda(self, params: dict):
        """Mostrar ayuda"""
        await self.send_message(
            "📚 **Guía de uso del chatbot**\n\n"
            "Puedes preguntarme de forma natural. Aquí algunos ejemplos:\n\n"
            "**Buscar lugares cercanos:**\n"
            "• \"Hospitales cercanos\"\n"
            "• \"Farmacias cerca\"\n"
            "• \"Bancos próximos\"\n"
            "• \"Gasolinera cercana\"\n\n"
            "**Listar por categoría:**\n"
            "• \"Hospital\" (palabra sola)\n"
            "• \"Lista las farmacias\"\n"
            "• \"Muestra los bancos\"\n\n"
            "**Buscar por nombre:**\n"
            "• \"¿Dónde está Hospital General?\"\n"
            "• \"Busca BBVA\"\n\n"
            "**Ver categorías:**\n"
            "• \"¿Qué categorías hay?\"\n\n"
            "💡 **Tip:** Puedes escribir de forma simple y directa."
        )

    async def handle_listar_categorias(self, params: dict):
        """Listar categorías disponibles con conteos"""
        try:
            query = """
                SELECT
                    categoria,
                    COUNT(*) AS total
                FROM poi
                WHERE activo = TRUE
                GROUP BY categoria
                ORDER BY categoria
            """
            rows = await db.fetch_all(query)

            if not rows:
                await self.send_message("No hay categorías disponibles en este momento.")
                return

            # Iconos por categoría
            icons = {
                "hospital": "🏥",
                "farmacia": "💊",
                "papeleria": "📝",
                "gasolinera": "⛽",
                "banco": "🏦"
            }

            response = "📋 **Categorías disponibles:**\n\n"
            for row in rows:
                categoria = row["categoria"]
                total = row["total"]
                icon = icons.get(categoria, "📍")
                categoria_display = categoria.capitalize()
                response += f"{icon} **{categoria_display}**: {total} lugares\n"

            response += "\n💡 Pregúntame sobre cualquiera de estas categorías."

            await self.send_message(response)

        except Exception as e:
            logger.error("handle_listar_categorias_error", error=str(e))
            await self.send_message("Ocurrió un error al consultar las categorías.")

    async def handle_listar_pois_categoria(self, params: dict):
        """Listar todos los POIs de una categoría"""
        categoria = params.get("categoria")

        if not categoria:
            await self.send_message("No pude identificar la categoría. ¿Puedes ser más específico?")
            return

        try:
            query = """
                SELECT
                    id,
                    nombre,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon,
                    categoria
                FROM poi
                WHERE activo = TRUE AND categoria = $1
                ORDER BY nombre
            """
            rows = await db.fetch_all(query, categoria)

            if not rows:
                await self.send_message(f"No encontré {categoria}s registrados.")
                return

            # Iconos por categoría
            icons = {
                "hospital": "🏥",
                "farmacia": "💊",
                "papeleria": "📝",
                "gasolinera": "⛽",
                "banco": "🏦"
            }
            icon = icons.get(categoria, "📍")
            categoria_display = categoria.capitalize()

            response = f"{icon} **{categoria_display}s encontrados** ({len(rows)}):\n\n"

            # Preparar datos para el mapa
            pois_data = []

            for idx, row in enumerate(rows, 1):
                response += f"**{idx}. {row['nombre']}**\n"
                if row["direccion"]:
                    response += f"   📍 {row['direccion']}\n"
                if row["telefono"]:
                    response += f"   ☎️ {row['telefono']}\n"
                if row["horario"]:
                    response += f"   🕐 {row['horario']}\n"
                response += "\n"

                # Agregar POI a la lista para el mapa
                pois_data.append({
                    "id": row["id"],
                    "nombre": row["nombre"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "categoria": row["categoria"],
                    "direccion": row["direccion"] or "",
                    "telefono": row["telefono"] or "",
                    "horario": row["horario"] or ""
                })

            response += f"💡 **Los lugares están resaltados en el mapa**"

            # Enviar mensaje con datos para el mapa
            await self.send_message(response, data={
                "action": "highlight_pois",
                "pois": pois_data,
                "zoom_to_fit": True
            })

        except Exception as e:
            logger.error("handle_listar_pois_categoria_error", error=str(e))
            await self.send_message(f"Ocurrió un error al buscar {categoria}s.")

    async def handle_buscar_cercanos(self, params: dict):
        """Buscar POIs cercanos (usa centro de Tapachula como referencia)"""
        categoria = params.get("categoria")

        if not categoria:
            await self.send_message("No pude identificar qué tipo de lugar buscas. ¿Puedes ser más específico?")
            return

        try:
            # Centro de Tapachula como referencia (convertir a string)
            lat_centro = "14.908598"
            lon_centro = "-92.252354"
            radio = 5000  # 5 km de radio

            query = """
                SELECT
                    id,
                    nombre,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon,
                    ROUND(ST_Distance(
                        ubicacion,
                        ST_GeogFromText('SRID=4326;POINT(' || $2 || ' ' || $1 || ')')
                    )::numeric, 0) AS distancia_m
                FROM poi
                WHERE activo = TRUE
                  AND categoria = $3
                  AND ST_DWithin(
                      ubicacion,
                      ST_GeogFromText('SRID=4326;POINT(' || $2 || ' ' || $1 || ')'),
                      $4
                  )
                ORDER BY distancia_m
                LIMIT 5
            """
            rows = await db.fetch_all(query, lat_centro, lon_centro, categoria, radio)

            if not rows:
                await self.send_message(f"No encontré {categoria}s cercanos en un radio de {radio/1000} km del centro de Tapachula.")
                return

            # Iconos por categoría
            icons = {
                "hospital": "🏥",
                "farmacia": "💊",
                "papeleria": "📝",
                "gasolinera": "⛽",
                "banco": "🏦"
            }
            icon = icons.get(categoria, "📍")
            categoria_display = categoria.capitalize()

            response = f"{icon} **{categoria_display}s más cercanos:**\n\n"

            # Preparar datos para el mapa
            pois_data = []

            for idx, row in enumerate(rows, 1):
                distancia_km = row['distancia_m'] / 1000
                response += f"**{idx}. {row['nombre']}** ({distancia_km:.1f} km)\n"
                if row["direccion"]:
                    response += f"   📍 {row['direccion']}\n"
                if row["telefono"]:
                    response += f"   ☎️ {row['telefono']}\n"
                if row["horario"]:
                    response += f"   🕐 {row['horario']}\n"
                response += "\n"

                # Agregar POI a la lista para el mapa
                pois_data.append({
                    "id": row["id"],
                    "nombre": row["nombre"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "categoria": categoria,
                    "direccion": row["direccion"] or "",
                    "telefono": row["telefono"] or "",
                    "horario": row["horario"] or "",
                    "distancia_m": int(row["distancia_m"])
                })

            response += f"💡 **Los lugares están resaltados en el mapa**"

            # Enviar mensaje con datos para el mapa
            await self.send_message(response, data={
                "action": "highlight_pois",
                "pois": pois_data,
                "zoom_to_fit": True,
                "center_point": {"lat": float(lat_centro), "lon": float(lon_centro)}
            })

        except Exception as e:
            logger.error("handle_buscar_cercanos_error", error=str(e))
            await self.send_message(f"Ocurrió un error al buscar {categoria}s cercanos.")

    async def handle_buscar_nombre(self, params: dict):
        """Buscar POI por nombre"""
        nombre = params.get("nombre")

        if not nombre:
            await self.send_message("No pude identificar el nombre del lugar. ¿Puedes ser más específico?")
            return

        try:
            # Búsqueda fuzzy por nombre
            search_pattern = f"%{nombre}%"

            query = """
                SELECT
                    id,
                    nombre,
                    categoria,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon
                FROM poi
                WHERE activo = TRUE
                  AND LOWER(nombre) LIKE LOWER($1)
                ORDER BY nombre
                LIMIT 5
            """
            rows = await db.fetch_all(query, search_pattern)

            if not rows:
                await self.send_message(f"No encontré lugares con el nombre \"{nombre}\".\n\n💡 Intenta buscar por categoría (hospital, farmacia, etc.)")
                return

            # Iconos por categoría
            icons = {
                "hospital": "🏥",
                "farmacia": "💊",
                "papeleria": "📝",
                "gasolinera": "⛽",
                "banco": "🏦"
            }

            # Preparar datos para el mapa
            pois_data = []

            for row in rows:
                pois_data.append({
                    "id": row["id"],
                    "nombre": row["nombre"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "categoria": row["categoria"],
                    "direccion": row["direccion"] or "",
                    "telefono": row["telefono"] or "",
                    "horario": row["horario"] or ""
                })

            if len(rows) == 1:
                row = rows[0]
                icon = icons.get(row["categoria"], "📍")
                response = f"{icon} **{row['nombre']}**\n\n"
                response += f"**Categoría:** {row['categoria'].capitalize()}\n"
                if row["direccion"]:
                    response += f"**Dirección:** {row['direccion']}\n"
                if row["telefono"]:
                    response += f"**Teléfono:** {row['telefono']}\n"
                if row["horario"]:
                    response += f"**Horario:** {row['horario']}\n"
                response += f"\n💡 **El lugar está resaltado en el mapa**"
            else:
                response = f"📍 **Encontré {len(rows)} lugares:**\n\n"
                for idx, row in enumerate(rows, 1):
                    icon = icons.get(row["categoria"], "📍")
                    response += f"**{idx}. {icon} {row['nombre']}**\n"
                    response += f"   Tipo: {row['categoria'].capitalize()}\n"
                    if row["direccion"]:
                        response += f"   📍 {row['direccion']}\n"
                    response += "\n"
                response += f"💡 **Los lugares están resaltados en el mapa**"

            # Enviar mensaje con datos para el mapa
            await self.send_message(response, data={
                "action": "highlight_pois",
                "pois": pois_data,
                "zoom_to_fit": True
            })

        except Exception as e:
            logger.error("handle_buscar_nombre_error", error=str(e))
            await self.send_message(f"Ocurrió un error al buscar \"{nombre}\".")

    async def send_message(self, text: str, data: dict = None):
        """
        Enviar mensaje al cliente con datos opcionales para el mapa.

        Args:
            text: Mensaje de texto para mostrar
            data: Datos estructurados opcionales (coordenadas, POIs, etc.)
        """
        try:
            message = {
                "type": "BOT_MESSAGE",
                "message": text,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Agregar datos estructurados si existen
            if data:
                message["data"] = data

            # Enviar como texto JSON con encoding UTF-8
            await self.websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error("send_message_error", session_id=self.session_id, error=str(e))
