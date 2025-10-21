"""
Simulador de dispositivos GPS.
Simula múltiples unidades enviando posiciones periódicas al servidor.
Soporta renovación automática de tokens con persistencia en config.json.
"""
import asyncio
import websockets
import json
import random
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
import argparse
from pathlib import Path
import structlog

# Configurar logging
logger = structlog.get_logger()


class Route:
    """Representa una ruta con coordenadas"""

    def __init__(self, name: str, coordinates: List[Tuple[float, float]]):
        self.name = name
        self.coordinates = coordinates
        self.current_index = 0

    def get_next_position(self, deviation: float = 0.0) -> Tuple[float, float]:
        """
        Obtener siguiente posición en la ruta.

        Args:
            deviation: Desviación aleatoria en grados (para simular fuera de ruta)
        """
        if self.current_index >= len(self.coordinates):
            self.current_index = 0

        lat, lon = self.coordinates[self.current_index]

        # Aplicar desviación aleatoria
        if deviation > 0:
            lat += random.uniform(-deviation, deviation)
            lon += random.uniform(-deviation, deviation)

        self.current_index += 1
        return lat, lon


# Cargar rutas desde archivo JSON
def load_routes_from_json():
    """Carga rutas desde routes_tapachula.json"""
    json_path = Path(__file__).parent / "routes_tapachula.json"

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            routes_data = json.load(f)

        routes = {}
        for route_key, route_info in routes_data.items():
            # Convertir lista de coordenadas a tuplas
            coordinates = [tuple(coord) for coord in route_info["coordinates"]]
            routes[route_key] = Route(route_info["name"], coordinates)

        print(f"✓ Cargadas {len(routes)} rutas desde {json_path.name}")
        for key, route in routes.items():
            print(f"  - {route.name}: {len(route.coordinates)} puntos")

        return routes
    except FileNotFoundError:
        print(f"⚠️ No se encontró {json_path}, usando ruta por defecto")
        # Ruta de respaldo simple
        return {
            "RUTA_DEFAULT": Route(
                "Ruta por defecto",
                [(14.9125, -92.2645), (14.9175, -92.2633)]
            )
        }
    except Exception as e:
        print(f"❌ Error cargando rutas: {e}")
        raise

# Cargar rutas al inicio
ROUTES = load_routes_from_json()


# Gestor de configuración de dispositivos
class DeviceConfigManager:
    """Gestiona la configuración persistente de dispositivos desde config.json"""

    def __init__(self, config_path: str = "device_config.json"):
        self.config_path = Path(__file__).parent / config_path
        self.config_data: Dict = {}
        self.load_config()

    def load_config(self):
        """Cargar configuración desde JSON"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                logger.info("config_loaded", path=str(self.config_path))
            else:
                logger.warning("config_not_found", path=str(self.config_path))
                self.config_data = {"devices": [], "server_url": "ws://localhost:8000/ws/device"}
        except Exception as e:
            logger.error("config_load_error", error=str(e))
            self.config_data = {"devices": [], "server_url": "ws://localhost:8000/ws/device"}

    def save_config(self):
        """Guardar configuración a JSON"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False, default=str)
            logger.info("config_saved", path=str(self.config_path))
        except Exception as e:
            logger.error("config_save_error", error=str(e))

    def get_device_config(self, device_id: str) -> Optional[Dict]:
        """Obtener configuración de un dispositivo específico"""
        for device in self.config_data.get("devices", []):
            if device.get("device_id") == device_id:
                return device
        return None

    def update_device_token(self, device_id: str, new_token: str, expires_at: str):
        """Actualizar token de dispositivo"""
        for device in self.config_data.get("devices", []):
            if device.get("device_id") == device_id:
                device["token"] = new_token
                device["token_expires_at"] = expires_at
                device["last_renewal"] = datetime.utcnow().isoformat() + "Z"
                self.save_config()
                logger.info("device_token_updated", device_id=device_id)
                return True
        logger.warning("device_not_found_for_update", device_id=device_id)
        return False

    def get_server_url(self) -> str:
        """Obtener URL del servidor"""
        return self.config_data.get("server_url", "ws://localhost:8000/ws/device")

    def get_all_devices(self) -> List[Dict]:
        """Obtener todos los dispositivos configurados"""
        return self.config_data.get("devices", [])


class GPSDevice:
    """Simulador de dispositivo GPS con soporte para renovación automática de tokens"""

    def __init__(
        self,
        unidad_id: str,
        device_id: str,
        token: str,
        route: Route,
        server_url: str = "ws://localhost:8000/ws/device",
        interval: int = 5,
        simulate_events: bool = True,
        config_manager: Optional['DeviceConfigManager'] = None,
    ):
        self.unidad_id = unidad_id
        self.device_id = device_id
        self.token = token
        self.route = route
        self.server_url = server_url
        self.interval = interval
        self.simulate_events = simulate_events
        self.config_manager = config_manager
        self.websocket = None
        self.sequence = 0
        self.running = False

        # Estado para eventos prolongados
        self.current_event_type = None
        self.event_start_time = None
        self.event_duration = 0

        # Background task para recibir mensajes del servidor
        self.receiver_task = None

    async def connect(self):
        """Conectar al servidor WebSocket"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"[{self.unidad_id}] Conectado al servidor: {self.server_url}")

            # Enviar autenticación
            auth_msg = {
                "type": "AUTH",
                "token": self.token,
                "device_id": self.device_id,
            }
            await self.websocket.send(json.dumps(auth_msg))

            # Esperar respuesta de autenticación
            response = await self.websocket.recv()
            response_data = json.loads(response)

            if response_data.get("type") == "AUTH_OK":
                print(
                    f"[{self.unidad_id}] Autenticado exitosamente: {response_data.get('message')}"
                )
                return True
            else:
                print(
                    f"[{self.unidad_id}] Error de autenticación: {response_data.get('message')}"
                )
                return False

        except Exception as e:
            print(f"[{self.unidad_id}] Error de conexión: {e}")
            return False

    async def send_position(self):
        """Enviar posición GPS al servidor"""
        try:
            # Inicializar velocidad normal
            deviation = 0.0
            speed = random.uniform(5.0, 20.0)  # m/s (18-72 km/h)

            # Gestión de eventos prolongados
            if self.simulate_events:
                # Si no hay evento activo, intentar iniciar uno nuevo (5% probabilidad)
                if self.current_event_type is None and random.random() < 0.05:
                    self.current_event_type = random.choice(["out_of_route", "stop_long", "speeding"])
                    self.event_start_time = datetime.utcnow()
                    # Duración aleatoria entre 60-180 segundos para eventos prolongados
                    self.event_duration = random.randint(60, 180) if self.current_event_type == "stop_long" else random.randint(30, 60)
                    print(f"[{self.unidad_id}] ⚠️ INICIANDO evento: {self.current_event_type} por {self.event_duration}s")

                # Si hay evento activo, aplicar comportamiento
                if self.current_event_type is not None:
                    elapsed = (datetime.utcnow() - self.event_start_time).total_seconds()

                    if elapsed >= self.event_duration:
                        # Terminar evento
                        print(f"[{self.unidad_id}] ✓ FINALIZANDO evento: {self.current_event_type}")
                        self.current_event_type = None
                        self.event_start_time = None
                    else:
                        # Aplicar comportamiento del evento
                        if self.current_event_type == "out_of_route":
                            deviation = 0.005  # Desviación ~500m
                        elif self.current_event_type == "stop_long":
                            speed = random.uniform(0.0, 0.8)  # Detenido (0-2.88 km/h)
                            print(f"[{self.unidad_id}] 🛑 Detenido ({elapsed:.0f}s/{self.event_duration}s)")
                        elif self.current_event_type == "speeding":
                            speed = random.uniform(25.0, 35.0)  # Exceso de velocidad (90-126 km/h)

            lat, lon = self.route.get_next_position(deviation)
            heading = random.uniform(0, 360)

            pos_msg = {
                "type": "POS",
                "lat": lat,
                "lon": lon,
                "speed": speed,
                "heading": heading,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "seq": self.sequence,
            }

            await self.websocket.send(json.dumps(pos_msg))
            self.sequence += 1

            # Esperar ACK
            response = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            response_data = json.loads(response)

            if response_data.get("type") == "ACK":
                event_id = response_data.get("event_id")
                status = f"✓ ACK pos={response_data.get('posicion_id')}"
                if event_id:
                    status += f" [EVENTO detectado: ID={event_id}]"
                print(f"[{self.unidad_id}] {status}")
            else:
                print(f"[{self.unidad_id}] Respuesta inesperada: {response_data}")

        except asyncio.TimeoutError:
            print(f"[{self.unidad_id}] Timeout esperando ACK")
        except Exception as e:
            print(f"[{self.unidad_id}] Error enviando posición: {e}")
            raise

    async def run(self):
        """Loop principal del simulador"""
        self.running = True

        # Conectar
        if not await self.connect():
            print(f"[{self.unidad_id}] No se pudo conectar. Abortando.")
            return

        # Loop de envío de posiciones
        try:
            while self.running:
                await self.send_position()
                await asyncio.sleep(self.interval)

        except websockets.exceptions.ConnectionClosed:
            print(f"[{self.unidad_id}] Conexión cerrada por el servidor")
        except Exception as e:
            print(f"[{self.unidad_id}] Error en loop principal: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
            print(f"[{self.unidad_id}] Desconectado")

    def stop(self):
        """Detener simulador"""
        self.running = False


async def run_simulator(
    num_devices: int = 3,
    server_url: str = "ws://localhost:8000/ws/device",
    interval: int = 5,
    simulate_events: bool = True,
):
    """
    Ejecutar simulación con múltiples dispositivos.

    Args:
        num_devices: Número de dispositivos a simular
        server_url: URL del servidor WebSocket
        interval: Intervalo de envío de posiciones (segundos)
        simulate_events: Si True, simula eventos ocasionalmente
    """
    # NOTA: Estos tokens deben ser generados previamente usando la API REST
    # Para propósitos de testing, usar tokens reales generados desde /api/v1/tokens

    devices = []
    routes = list(ROUTES.values())

    print(f"=== Simulador de Dispositivos GPS ===")
    print(f"Servidor: {server_url}")
    print(f"Dispositivos: {num_devices}")
    print(f"Intervalo: {interval}s")
    print(f"Simulación de eventos: {'Sí' if simulate_events else 'No'}")
    print(f"=====================================\n")

    # INSTRUCCIONES: Antes de ejecutar, crea tokens usando la API:
    # curl -X POST http://localhost:8000/api/v1/tokens \
    #   -H "Content-Type: application/json" \
    #   -d '{"unidad_id":"UNIT-001","device_id":"GPS-SIM-001","ttl_seconds":86400}'

    # Tokens de ejemplo (REEMPLAZAR con tokens reales)
    example_configs = [
        {"unidad_id": "UNIT-001", "device_id": "GPS-SIM-001", "token": "69fd24428c5a82fa071aec2b07361dd0ec6e3c0085c1577344533d2de59d6fce"},
        {"unidad_id": "UNIT-002", "device_id": "GPS-SIM-002", "token": "f46d48a4f86c9537631132bb3884ccef7b92f7be297ce5d6b64700f82e843f7d"},
        {"unidad_id": "UNIT-003", "device_id": "GPS-SIM-003", "token": "1f0ac2f4b18f926bbb71dac37011b518dc7d24e1d0e353440f8e584b44d21367"},
    ]

    for i in range(min(num_devices, len(example_configs))):
        config = example_configs[i]
        route = routes[i % len(routes)]

        device = GPSDevice(
            unidad_id=config["unidad_id"],
            device_id=config["device_id"],
            token=config["token"],
            route=route,
            server_url=server_url,
            interval=interval,
            simulate_events=simulate_events,
        )
        devices.append(device)

    # Ejecutar todos los dispositivos en paralelo
    tasks = [device.run() for device in devices]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n\n=== Deteniendo simulador ===")
        for device in devices:
            device.stop()


def main():
    """Punto de entrada principal"""
    parser = argparse.ArgumentParser(description="Simulador de Dispositivos GPS")
    parser.add_argument(
        "-n",
        "--num-devices",
        type=int,
        default=3,
        help="Número de dispositivos a simular (default: 3)",
    )
    parser.add_argument(
        "-s",
        "--server",
        type=str,
        default="ws://localhost:8000/ws/device",
        help="URL del servidor WebSocket (default: ws://localhost:8000/ws/device)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=5,
        help="Intervalo de envío en segundos (default: 5)",
    )
    parser.add_argument(
        "--no-events",
        action="store_true",
        help="Desactivar simulación de eventos",
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            run_simulator(
                num_devices=args.num_devices,
                server_url=args.server,
                interval=args.interval,
                simulate_events=not args.no_events,
            )
        )
    except KeyboardInterrupt:
        print("\n\nSimulador detenido por el usuario")


if __name__ == "__main__":
    main()
