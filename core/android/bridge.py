"""
AndroidBridge - WebSocket client for communicating with Android app
"""

import asyncio
import json
import websockets
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class AndroidDevice:
    """Android device information."""
    device_id: str
    name: str
    ip: str
    port: int
    paired: bool = False
    last_seen: float = 0
    capabilities: List[str] = field(default_factory=list)
    
    @property
    def ws_url(self) -> str:
        return f"ws://{self.ip}:{self.port}/ws"


class AndroidBridge:
    """WebSocket bridge to Android device."""
    
    def __init__(
        self,
        device: AndroidDevice,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_state_change: Optional[Callable[[ConnectionState], None]] = None,
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
    ):
        self.device = device
        self.on_message = on_message
        self.on_state_change = on_state_change
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._state = ConnectionState.DISCONNECTED
        self._running = False
        self._message_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._logger = logging.getLogger("AndroidBridge")
    
    @property
    def state(self) -> ConnectionState:
        return self._state
    
    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED
    
    def _set_state(self, state: ConnectionState) -> None:
        self._state = state
        if self.on_state_change:
            self.on_state_change(state)
    
    async def connect(self) -> bool:
        """Connect to Android device."""
        if self._state == ConnectionState.CONNECTED:
            return True
        
        self._set_state(ConnectionState.CONNECTING)
        self._running = True
        
        try:
            self._ws = await websockets.connect(
                self.device.ws_url,
                ping_interval=20,
                ping_timeout=10,
            )
            self._set_state(ConnectionState.CONNECTED)
            self.device.paired = True
            
            # Start message handler
            asyncio.create_task(self._message_loop())
            return True
            
        except Exception as e:
            self._logger.error(f"Connection failed: {e}")
            self._set_state(ConnectionState.ERROR)
            if self.auto_reconnect:
                asyncio.create_task(self._reconnect_loop())
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from device."""
        self._running = False
        self._set_state(ConnectionState.DISCONNECTED)
        
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    async def _reconnect_loop(self) -> None:
        """Auto-reconnect loop."""
        while self._running and self.auto_reconnect:
            await asyncio.sleep(self.reconnect_interval)
            if self._running and self._state != ConnectionState.CONNECTED:
                self._logger.info("Attempting reconnect...")
                await self.connect()
    
    async def _message_loop(self) -> None:
        """Handle incoming messages."""
        try:
            async for message in self._ws:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            self._logger.info("Connection closed")
            self._set_state(ConnectionState.DISCONNECTED)
            if self.auto_reconnect:
                asyncio.create_task(self._reconnect_loop())
        except Exception as e:
            self._logger.error(f"Message loop error: {e}")
            self._set_state(ConnectionState.ERROR)
    
    async def _handle_message(self, message: str) -> None:
        """Process incoming message."""
        try:
            data = json.loads(message)
            
            # Handle response to pending request
            msg_id = data.get("id")
            if msg_id and msg_id in self._pending_requests:
                future = self._pending_requests.pop(msg_id)
                if not future.done():
                    future.set_result(data)
                return
            
            # Handle notifications/events
            if self.on_message:
                self.on_message(data)
                
        except json.JSONDecodeError:
            self._logger.warning(f"Invalid JSON: {message}")
        except Exception as e:
            self._logger.error(f"Message handling error: {e}")
    
    async def send_request(
        self,
        action: str,
        params: Dict[str, Any] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Send request and wait for response."""
        if not self.is_connected:
            raise ConnectionError("Not connected to device")
        
        self._message_id += 1
        msg_id = self._message_id
        
        request = {
            "id": msg_id,
            "action": action,
            "params": params or {},
        }
        
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[msg_id] = future
        
        try:
            await self._ws.send(json.dumps(request))
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._pending_requests.pop(msg_id, None)
            raise TimeoutError(f"Request {action} timed out")
        except Exception as e:
            self._pending_requests.pop(msg_id, None)
            raise
    
    async def send_notification(self, action: str, params: Dict[str, Any] = None) -> None:
        """Send notification (no response expected)."""
        if not self.is_connected:
            raise ConnectionError("Not connected to device")
        
        notification = {
            "action": action,
            "params": params or {},
        }
        await self._ws.send(json.dumps(notification))
    
    # Convenience methods for common actions
    async def open_app(self, package_name: str) -> Dict[str, Any]:
        return await self.send_request("open_app", {"package": package_name})
    
    async def tap(self, x: int, y: int) -> Dict[str, Any]:
        return await self.send_request("tap", {"x": x, "y": y})
    
    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> Dict[str, Any]:
        return await self.send_request("swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration})
    
    async def type_text(self, text: str) -> Dict[str, Any]:
        return await self.send_request("type_text", {"text": text})
    
    async def get_notifications(self) -> Dict[str, Any]:
        return await self.send_request("get_notifications", {})
    
    async def media_control(self, action: str) -> Dict[str, Any]:
        return await self.send_request("media_control", {"action": action})
    
    async def answer_call(self) -> Dict[str, Any]:
        return await self.send_request("answer_call", {})
    
    async def decline_call(self) -> Dict[str, Any]:
        return await self.send_request("decline_call", {})
    
    async def open_youtube(self, query: str = "") -> Dict[str, Any]:
        return await self.send_request("open_youtube", {"query": query})
    
    async def get_screen_state(self) -> Dict[str, Any]:
        return await self.send_request("get_screen_state", {})
    
    async def take_screenshot(self) -> Dict[str, Any]:
        return await self.send_request("take_screenshot", {})
    
    async def get_device_info(self) -> Dict[str, Any]:
        return await self.send_request("get_device_info", {})


class AndroidBridgeManager:
    """Manage multiple Android device bridges."""
    
    def __init__(self):
        self._bridges: Dict[str, AndroidBridge] = {}
        self._devices: Dict[str, AndroidDevice] = {}
    
    def add_device(self, device: AndroidDevice) -> None:
        self._devices[device.device_id] = device
    
    def remove_device(self, device_id: str) -> None:
        self._devices.pop(device_id, None)
        if device_id in self._bridges:
            asyncio.create_task(self._bridges[device_id].disconnect())
            self._bridges.pop(device_id, None)
    
    def get_bridge(self, device_id: str) -> Optional[AndroidBridge]:
        return self._bridges.get(device_id)
    
    async def connect_device(self, device_id: str) -> bool:
        device = self._devices.get(device_id)
        if not device:
            return False
        
        bridge = AndroidBridge(device)
        self._bridges[device_id] = bridge
        return await bridge.connect()
    
    async def disconnect_device(self, device_id: str) -> None:
        bridge = self._bridges.get(device_id)
        if bridge:
            await bridge.disconnect()
            self._bridges.pop(device_id, None)
    
    async def disconnect_all(self) -> None:
        for bridge in self._bridges.values():
            await bridge.disconnect()
        self._bridges.clear()
    
    def list_devices(self) -> List[AndroidDevice]:
        return list(self._devices.values())


# Global manager
_bridge_manager = AndroidBridgeManager()


def get_bridge_manager() -> AndroidBridgeManager:
    return _bridge_manager