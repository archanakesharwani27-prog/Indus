"""
DeviceManager - Android device discovery, pairing, and management
"""

import asyncio
import json
import socket
import hashlib
import secrets
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import threading
import time

from core.android.bridge import AndroidDevice, AndroidBridgeManager, get_bridge_manager


@dataclass
class PairingInfo:
    """Pairing information."""
    device_id: str
    pin: str
    expires_at: float
    confirmed: bool = False


class DeviceManager:
    """Manage Android device discovery, pairing, and connections."""
    
    def __init__(self):
        self._bridge_manager = get_bridge_manager()
        self._pairing_codes: Dict[str, PairingInfo] = {}
        self._discovery_running = False
        self._discovery_thread: Optional[threading.Thread] = None
        self._on_device_found: Optional[Callable[[AndroidDevice], None]] = None
        self._on_device_paired: Optional[Callable[[AndroidDevice], None]] = None
        self._on_device_connected: Optional[Callable[[AndroidDevice], None]] = None
        self._on_device_disconnected: Optional[Callable[[AndroidDevice], None]] = None
    
    # Callback setters
    def set_on_device_found(self, callback: Callable[[AndroidDevice], None]) -> None:
        self._on_device_found = callback
    
    def set_on_device_paired(self, callback: Callable[[AndroidDevice], None]) -> None:
        self._on_device_paired = callback
    
    def set_on_device_connected(self, callback: Callable[[AndroidDevice], None]) -> None:
        self._on_device_connected = callback
    
    def set_on_device_disconnected(self, callback: Callable[[AndroidDevice], None]) -> None:
        self._on_device_disconnected = callback
    
    # Device discovery
    def start_discovery(self, port: int = 8765, broadcast_ip: str = "255.255.255.255") -> None:
        """Start mDNS/broadcast discovery for Android devices."""
        if self._discovery_running:
            return
        
        self._discovery_running = True
        self._discovery_thread = threading.Thread(
            target=self._discovery_loop,
            args=(port, broadcast_ip),
            daemon=True,
        )
        self._discovery_thread.start()
    
    def stop_discovery(self) -> None:
        """Stop device discovery."""
        self._discovery_running = False
        if self._discovery_thread:
            self._discovery_thread.join(timeout=2)
    
    def _discovery_loop(self, port: int, broadcast_ip: str) -> None:
        """Discovery loop (broadcast UDP)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2.0)
        
        # Bind to receive responses
        try:
            sock.bind(("", port))
        except OSError:
            sock.bind(("", 0))
        
        discovery_msg = json.dumps({
            "type": "indus_discover",
            "version": "1.0",
        }).encode()
        
        while self._discovery_running:
            try:
                # Send discovery broadcast
                sock.sendto(discovery_msg, (broadcast_ip, port))
                
                # Listen for responses
                try:
                    data, addr = sock.recvfrom(4096)
                    response = json.loads(data.decode())
                    self._handle_discovery_response(response, addr[0])
                except socket.timeout:
                    pass
                except json.JSONDecodeError:
                    pass
                
                time.sleep(5)  # Discover every 5 seconds
            except Exception:
                pass
        
        sock.close()
    
    def _handle_discovery_response(self, response: Dict[str, Any], ip: str) -> None:
        """Handle device discovery response."""
        if response.get("type") != "indus_device":
            return
        
        device = AndroidDevice(
            device_id=response.get("device_id", ""),
            name=response.get("name", "Unknown Device"),
            ip=ip,
            port=response.get("port", 8765),
            capabilities=response.get("capabilities", []),
        )
        
        if device.device_id:
            self._bridge_manager.add_device(device)
            if self._on_device_found:
                self._on_device_found(device)
    
    # Pairing
    def generate_pairing_code(self, device_id: str) -> Optional[str]:
        """Generate pairing code for device."""
        device = self._bridge_manager._devices.get(device_id)
        if not device:
            return None
        
        # Generate 6-digit PIN
        pin = str(secrets.randbelow(900000) + 100000)
        
        pairing = PairingInfo(
            device_id=device_id,
            pin=pin,
            expires_at=time.time() + 300,  # 5 minutes
        )
        
        self._pairing_codes[device_id] = pairing
        return pin
    
    def verify_pairing_code(self, device_id: str, pin: str) -> bool:
        """Verify pairing code from Android app."""
        pairing = self._pairing_codes.get(device_id)
        if not pairing:
            return False
        
        if time.time() > pairing.expires_at:
            self._pairing_codes.pop(device_id, None)
            return False
        
        if pairing.pin != pin:
            return False
        
        pairing.confirmed = True
        return True
    
    def confirm_pairing(self, device_id: str) -> bool:
        """Confirm pairing (called after user approval)."""
        pairing = self._pairing_codes.get(device_id)
        if not pairing or not pairing.confirmed:
            return False
        
        device = self._bridge_manager._devices.get(device_id)
        if device:
            device.paired = True
            self._pairing_codes.pop(device_id, None)
            if self._on_device_paired:
                self._on_device_paired(device)
            return True
        return False
    
    def get_pairing_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get pairing status for device."""
        pairing = self._pairing_codes.get(device_id)
        if not pairing:
            return None
        
        return {
            "device_id": device_id,
            "pin": pairing.pin,
            "expires_in": max(0, int(pairing.expires_at - time.time())),
            "confirmed": pairing.confirmed,
        }
    
    # Connection management
    async def connect_device(self, device_id: str) -> bool:
        """Connect to paired device."""
        device = self._bridge_manager._devices.get(device_id)
        if not device or not device.paired:
            return False
        
        success = await self._bridge_manager.connect_device(device_id)
        if success and self._on_device_connected:
            self._on_device_connected(device)
        return success
    
    async def disconnect_device(self, device_id: str) -> None:
        """Disconnect device."""
        device = self._bridge_manager._devices.get(device_id)
        await self._bridge_manager.disconnect_device(device_id)
        if device and self._on_device_disconnected:
            self._on_device_disconnected(device)
    
    async def connect_all_paired(self) -> int:
        """Connect to all paired devices."""
        count = 0
        for device in self._bridge_manager.list_devices():
            if device.paired:
                if await self.connect_device(device.device_id):
                    count += 1
        return count
    
    # Device listing
    def list_devices(self) -> List[AndroidDevice]:
        return self._bridge_manager.list_devices()
    
    def get_device(self, device_id: str) -> Optional[AndroidDevice]:
        return self._bridge_manager._devices.get(device_id)
    
    def get_bridge(self, device_id: str):
        return self._bridge_manager.get_bridge(device_id)
    
    # QR code pairing
    def generate_qr_data(self, device_id: str) -> Optional[str]:
        """Generate QR code data for pairing."""
        device = self._bridge_manager._devices.get(device_id)
        if not device:
            return None
        
        pin = self.generate_pairing_code(device_id)
        if not pin:
            return None
        
        qr_data = {
            "type": "indus_pair",
            "device_id": device_id,
            "name": device.name,
            "ip": device.ip,
            "port": device.port,
            "pin": pin,
        }
        return json.dumps(qr_data)


# Global manager
_device_manager = DeviceManager()


def get_device_manager() -> DeviceManager:
    return _device_manager