"""
Simulador de dispositivos GPS con renovación automática de tokens.
Usa device_config.json para persistencia de tokens entre reinicios.
"""
import asyncio
import websockets
import json
import random
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
import argparse
from pathlib import Path

# Cargar rutas desde archivo JSON
def load_routes_from_json():
    """Carga rutas desde routes_tapachula.json"""
    json_path = Path(__file__).parent / "routes_tapachula.json"

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            routes_data = json.load(f)

        routes = {}
        for route_key, route_info in routes_data.items():
            coordinates = [tuple(coord) for coord in route_info["coordinates"]]
            routes[route_key] = Route(route_info["name"], coordinates)

        print(f"✓ Cargadas {len(routes)} rutas desde {json_path.name}")
        for key, route in routes.items():
            print(f"  - {route.name}: {len(route.coordinates)} puntos")

        return routes
    except FileNotFoundError:
        print(f"⚠️ No se encontró {json_path}, usando ruta por defecto")
        return {
            "RUTA_DEFAULT": Route(
                "Ruta por defecto",
                [(14.9125, -92.2645), (14.9175, -92.2633)]
            )
        }
    except Exception as e:
        print(f"❌ Error cargando rutas: {e}")
        raise


class Route:
    """Representa una ruta con coordenadas"""

    def __init__(self, name: str, coordinates: List[Tuple[float, float]]):
        self.name = name
        self.coordinates = coordinates
        self.current_index = 0

    def get_next_position(self, deviation: float = 0.0) -> Tuple[float, float]:
        if self.current_index >= len(self.coordinates):
            self.current_index = 0

        lat, lon = self.coordinates[self.current_index]

        if deviation > 0:
            lat += random.uniform(-deviation, deviation)
            lon += random.uniform(-deviation, deviation)

        self.current_index += 1
        return lat, lon


class DeviceConfigManager:
    """Gestiona configuración persistente de dispositivos en JSON"""

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
                print(f"✓ Configuración cargada desde {self.config_path.name}")
            else:
                print(f"⚠️ No se encontró {self.config_path.name}")
                self.config_data = {"devices": [], "server_url": "ws://localhost:8000/ws/device"}
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            self.config_data = {"devices": [], "server_url": "ws://localhost:8000/ws/device"}

    def save_config(self):
        """Guardar configuración a JSON"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"✓ Configuración guardada en {self.config_path.name}")
        except Exception as e:
            print(f"❌ Error guardando configuración: {e}")

    def get_device_config(self, device_id: str) -> Optional[Dict]:
        """Obtener configuración de dispositivo"""
        for device in self.config_data.get("devices", []):
            if device.get("device_id") == device_id:
                return device
        return None

    def update_device_token(self, device_id: str, new_token: str, expires_at: str):
        """Actualizar token de dispositivo con logs detallados"""
        for device in self.config_data.get("devices", []):
            if device.get("device_id") == device_id:
                # Guardar token anterior para comparación
                old_token_preview = device.get("token", "N/A")[:8] + "..." if device.get("token") else "N/A"

                # Actualizar token
                device["token"] = new_token
                device["token_expires_at"] = expires_at
                now = datetime.utcnow().isoformat() + "Z"
                device["last_renewal"] = now

                # Guardar configuración
                self.save_config()

                # Logs detallados
                print(f"\n{'='*60}")
                print(f"[{device_id}] 📝 TOKEN ACTUALIZADO EN device_config.json")
                print(f"{'='*60}")
                print(f"  Token anterior:  {old_token_preview}")
                print(f"  Token nuevo:     {new_token[:8]}...{new_token[-8:]}")
                print(f"  Expira:          {expires_at}")
                print(f"  Guardado:        {now}")
                print(f"  Archivo:         {self.config_path}")
                print(f"{'='*60}\n")

                return True
        print(f"[{device_id}] ⚠️ Dispositivo no encontrado en config")
        return False

    def get_server_url(self) -> str:
        return self.config_data.get("server_url", "ws://localhost:8000/ws/device")

    def get_all_devices(self) -> List[Dict]:
        return self.config_data.get("devices", [])


class GPSDevice:
    """Simulador de dispositivo GPS con renovación automática de tokens"""

    def __init__(
        self,
        unidad_id: str,
        device_id: str,
        token: str,
        route: Route,
        server_url: str = "ws://localhost:8000/ws/device",
        interval: int = 5,
        simulate_events: bool = True,
        config_manager: Optional[DeviceConfigManager] = None,
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

        # Task para recibir mensajes del servidor (renovaciones)
        self.receiver_task = None

    async def connect(self):
        """Conectar al servidor WebSocket"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"[{self.unidad_id}] 🔌 Conectado al servidor: {self.server_url}")

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
                print(f"[{self.unidad_id}] ✓ Autenticado: {response_data.get('message')}")
                return True
            else:
                print(f"[{self.unidad_id}] ❌ Error de autenticación: {response_data.get('message')}")
                return False

        except Exception as e:
            print(f"[{self.unidad_id}] ❌ Error de conexión: {e}")
            return False

    async def message_receiver(self):
        """Recibir mensajes del servidor (renovaciones de token)"""
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    message_data = json.loads(message)

                    msg_type = message_data.get("type")

                    # Manejar renovación de token
                    if msg_type == "TOKEN_RENEWAL":
                        await self.handle_token_renewal(message_data)
                    elif msg_type == "ACK":
                        # ACKs se manejan en send_position
                        pass
                    else:
                        print(f"[{self.unidad_id}] ℹ️ Mensaje recibido: {msg_type}")

                except asyncio.TimeoutError:
                    # Timeout normal, continuar
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print(f"[{self.unidad_id}] ⚠️ Conexión cerrada en receiver")
                    break

        except Exception as e:
            print(f"[{self.unidad_id}] ❌ Error en message receiver: {e}")

    async def handle_token_renewal(self, renewal_data: Dict):
        """Manejar notificación de renovación de token"""
        try:
            new_token = renewal_data.get("new_token")
            expires_at = renewal_data.get("expires_at")
            grace_period = renewal_data.get("grace_period_days", 7)
            message = renewal_data.get("message", "Token renovado")

            print(f"\n{'='*70}")
            print(f"[{self.unidad_id}] 🔄 RENOVACIÓN DE TOKEN RECIBIDA DEL SERVIDOR")
            print(f"{'='*70}")
            print(f"  Mensaje:         {message}")
            print(f"  Token anterior:  {self.token[:8]}...{self.token[-8:]}")
            print(f"  Token nuevo:     {new_token[:8]}...{new_token[-8:]}")
            print(f"  Nueva expiración: {expires_at}")
            print(f"  Grace period:    {grace_period} días")
            print(f"{'='*70}")

            # Actualizar token en memoria
            old_token = self.token
            self.token = new_token

            # Guardar en config.json
            if self.config_manager:
                print(f"[{self.unidad_id}] 💾 Guardando token en device_config.json...")
                success = self.config_manager.update_device_token(
                    self.device_id,
                    new_token,
                    expires_at
                )

                # Enviar confirmación al servidor
                ack_msg = {
                    "type": "TOKEN_RENEWAL_ACK",
                    "new_token_saved": success,
                    "device_id": self.device_id,
                    "message": "Token guardado exitosamente" if success else "Error al guardar token"
                }
                await self.websocket.send(json.dumps(ack_msg))

                if success:
                    print(f"[{self.unidad_id}] ✅ Confirmación enviada al servidor: TOKEN_RENEWAL_ACK")
                else:
                    print(f"[{self.unidad_id}] ⚠️ Token renovado en memoria pero no guardado en disco")
            else:
                print(f"[{self.unidad_id}] ⚠️ Config manager no disponible, token solo en memoria")

        except Exception as e:
            print(f"[{self.unidad_id}] ❌ Error manejando renovación: {e}")

    async def send_position(self):
        """Enviar posición GPS al servidor"""
        try:
            deviation = 0.0
            speed = random.uniform(5.0, 20.0)

            # Gestión de eventos
            if self.simulate_events:
                if self.current_event_type is None and random.random() < 0.05:
                    self.current_event_type = random.choice(["out_of_route", "stop_long", "speeding"])
                    self.event_start_time = datetime.utcnow()
                    self.event_duration = random.randint(60, 180) if self.current_event_type == "stop_long" else random.randint(30, 60)
                    print(f"[{self.unidad_id}] ⚠️ Evento: {self.current_event_type} por {self.event_duration}s")

                if self.current_event_type is not None:
                    elapsed = (datetime.utcnow() - self.event_start_time).total_seconds()

                    if elapsed >= self.event_duration:
                        print(f"[{self.unidad_id}] ✓ Fin evento: {self.current_event_type}")
                        self.current_event_type = None
                    else:
                        if self.current_event_type == "out_of_route":
                            deviation = 0.005
                        elif self.current_event_type == "stop_long":
                            speed = random.uniform(0.0, 0.8)
                        elif self.current_event_type == "speeding":
                            speed = random.uniform(25.0, 35.0)

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

        except Exception as e:
            print(f"[{self.unidad_id}] ❌ Error enviando posición: {e}")
            raise

    async def run(self):
        """Loop principal del simulador"""
        self.running = True

        # Conectar
        if not await self.connect():
            print(f"[{self.unidad_id}] No se pudo conectar. Abortando.")
            return

        # Iniciar receiver task para renovaciones
        self.receiver_task = asyncio.create_task(self.message_receiver())

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
            self.running = False
            if self.receiver_task:
                self.receiver_task.cancel()
            if self.websocket:
                await self.websocket.close()
            print(f"[{self.unidad_id}] Desconectado")

    def stop(self):
        """Detener simulador"""
        self.running = False


async def run_simulator_from_config(config_path: str = "device_config.json", interval: int = 5):
    """Ejecutar simulador usando configuración desde JSON"""

    # Cargar rutas
    routes_dict = load_routes_from_json()
    routes = list(routes_dict.values())

    # Cargar configuración de dispositivos
    config_manager = DeviceConfigManager(config_path)
    device_configs = config_manager.get_all_devices()

    if not device_configs:
        print(f"\n❌ No hay dispositivos configurados en {config_path}")
        print(f"Por favor edite el archivo y agregue dispositivos con tokens válidos.\n")
        return

    server_url = config_manager.get_server_url()

    print(f"\n=== Simulador GPS con Renovación Automática ===")
    print(f"Servidor: {server_url}")
    print(f"Dispositivos configurados: {len(device_configs)}")
    print(f"Intervalo: {interval}s")
    print(f"Config file: {config_path}")
    print(f"==============================================\n")

    devices = []

    for i, device_config in enumerate(device_configs):
        unidad_id = device_config.get("unidad_id")
        device_id = device_config.get("device_id")
        token = device_config.get("token")

        if token == "REPLACE_WITH_REAL_TOKEN":
            print(f"⚠️ Saltando {device_id}: Token no configurado")
            continue

        route = routes[i % len(routes)]

        device = GPSDevice(
            unidad_id=unidad_id,
            device_id=device_id,
            token=token,
            route=route,
            server_url=server_url,
            interval=interval,
            simulate_events=True,
            config_manager=config_manager,
        )
        devices.append(device)

    if not devices:
        print(f"\n❌ No hay dispositivos con tokens válidos")
        return

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
    parser = argparse.ArgumentParser(
        description="Simulador GPS con renovación automática de tokens"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="device_config.json",
        help="Archivo de configuración JSON (default: device_config.json)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=5,
        help="Intervalo de envío en segundos (default: 5)",
    )

    args = parser.parse_args()

    try:
        asyncio.run(run_simulator_from_config(
            config_path=args.config,
            interval=args.interval
        ))
    except KeyboardInterrupt:
        print("\n\nSimulador detenido por el usuario")


if __name__ == "__main__":
    main()
