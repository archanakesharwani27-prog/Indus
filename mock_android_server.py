"""
Mock Android WebSocket Server - Simulates IndusDroid for PC-side testing
Run this in a separate terminal, then test PC-side skills
"""

import asyncio
import json
import websockets
import logging
from typing import Dict, Any, Set
from dataclasses import dataclass, field
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MockAndroid")

# Simulated device state
@dataclass
class MockDeviceState:
    device_id: str = "android_mock_001"
    name: str = "Mock Android Device"
    paired: bool = True
    screen_on: bool = True
    current_app: str = "com.android.launcher"
    volume: int = 50
    muted: bool = False
    media_playing: bool = False
    notifications: list = field(default_factory=list)
    
    def __post_init__(self):
        # Add some mock notifications
        self.notifications = [
            {"packageName": "com.whatsapp", "title": "Ansh", "text": "Hey, how are you?", "timestamp": 1234567890, "id": 1},
            {"packageName": "com.google.android.gm", "title": "GitHub", "text": "New pull request", "timestamp": 1234567891, "id": 2},
            {"packageName": "com.android.chrome", "title": "Download complete", "text": "file.pdf downloaded", "timestamp": 1234567892, "id": 3},
        ]


class MockAndroidServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.state = MockDeviceState()
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.message_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
    
    async def register_client(self, ws: websockets.WebSocketServerProtocol):
        self.clients.add(ws)
        logger.info(f"Client connected. Total: {len(self.clients)}")
        
        # Send device info on connect
        await self.send_to_client(ws, {
            "action": "device_connected",
            "params": {
                "deviceId": self.state.device_id,
                "name": self.state.name,
                "capabilities": ["accessibility", "notifications", "media", "calls", "apps"]
            }
        })
    
    async def unregister_client(self, ws: websockets.WebSocketServerProtocol):
        self.clients.discard(ws)
        logger.info(f"Client disconnected. Total: {len(self.clients)}")
    
    async def send_to_client(self, ws: websockets.WebSocketServerProtocol, message: dict):
        try:
            await ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Send failed: {e}")
    
    async def broadcast(self, message: dict):
        if self.clients:
            await asyncio.gather(
                *[self.send_to_client(client, message) for client in self.clients],
                return_exceptions=True
            )
    
    async def handle_message(self, ws: websockets.WebSocketServerProtocol, text: str):
        try:
            message = json.loads(text)
            logger.info(f"Received: {message.get('action')} (id: {message.get('id')})")
            
            action = message.get("action")
            msg_id = message.get("id")
            params = message.get("params", {})
            
            # Handle requests from PC
            response = await self.process_action(action, params)
            
            # Send response if this was a request (has id)
            if msg_id is not None:
                await self.send_to_client(ws, {
                    "action": "response",
                    "id": msg_id,
                    "success": response.get("success", True),
                    "error": response.get("error"),
                    "result": response.get("result")
                })
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {text}")
        except Exception as e:
            logger.error(f"Handle message error: {e}")
    
    async def process_action(self, action: str, params: dict) -> dict:
        """Process action and return response data"""
        
        if action == "tap":
            x, y = params.get("x", 0), params.get("y", 0)
            logger.info(f"Mock tap at ({x}, {y})")
            return {"success": True, "result": {"x": x, "y": y}}
        
        elif action == "swipe":
            x1, y1 = params.get("x1", 0), params.get("y1", 0)
            x2, y2 = params.get("x2", 0), params.get("y2", 0)
            logger.info(f"Mock swipe ({x1},{y1}) -> ({x2},{y2})")
            return {"success": True}
        
        elif action == "type_text":
            text = params.get("text", "")
            logger.info(f"Mock type: '{text}'")
            return {"success": True}
        
        elif action == "open_app":
            package = params.get("package", "")
            self.state.current_app = package
            logger.info(f"Mock open app: {package}")
            return {"success": True}
        
        elif action == "get_notifications":
            logger.info("Mock get notifications")
            return {"success": True, "result": {"notifications": self.state.notifications}}
        
        elif action == "media_control":
            media_action = params.get("action", "")
            if media_action == "play":
                self.state.media_playing = True
            elif media_action == "pause":
                self.state.media_playing = False
            logger.info(f"Mock media: {media_action}")
            return {"success": True}
        
        elif action == "answer_call":
            logger.info("Mock answer call")
            return {"success": True}
        
        elif action == "decline_call":
            logger.info("Mock decline call")
            return {"success": True}
        
        elif action == "open_youtube":
            query = params.get("query", "")
            logger.info(f"Mock open YouTube: {query}")
            return {"success": True}
        
        elif action == "take_screenshot":
            logger.info("Mock screenshot")
            return {"success": False, "error": "Requires MediaProjection"}
        
        elif action == "get_device_info":
            return {
                "success": True,
                "result": {
                    "info": {
                        "deviceId": self.state.device_id,
                        "name": self.state.name,
                        "model": "Pixel 7 (Mock)",
                        "manufacturer": "Google",
                        "androidVersion": "14",
                        "sdkInt": 34,
                        "screenWidth": 1080,
                        "screenHeight": 2400,
                        "density": 2.75
                    }
                }
            }
        
        elif action == "get_screen_state":
            return {
                "success": True,
                "result": {
                    "topPackage": self.state.current_app,
                    "topClass": "MainActivity"
                }
            }
        
        elif action == "ping":
            return {"success": True}
        
        elif action == "device_connect":
            logger.info(f"Device connect: {params}")
            return {"success": True}
        
        else:
            logger.warning(f"Unknown action: {action}")
            return {"success": False, "error": f"Unknown action: {action}"}
    
    async def client_handler(self, ws: websockets.WebSocketServerProtocol):
        await self.register_client(ws)
        try:
            async for message in ws:
                await self.handle_message(ws, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(ws)
    
    async def start(self):
        logger.info(f"Starting Mock Android WebSocket Server on ws://{self.host}:{self.port}")
        async with websockets.serve(self.client_handler, self.host, self.port):
            await asyncio.Future()  # Run forever


async def main():
    server = MockAndroidServer()
    await server.start()


if __name__ == "__main__":
    print("=" * 50)
    print("Mock Android WebSocket Server")
    print("Listening on ws://0.0.0.0:8765")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")