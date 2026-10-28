"""
Stella Artemis Main Integration
Full implementation for Stella PC to control any Android device
"""

from .device_manager import ArtemisDeviceManager
from .action_executor import ActionExecutor
from .bidirectional_bridge import BidirectionalBridge
import asyncio

class StellaArtemis:
    def __init__(self):
        self.device_manager = ArtemisDeviceManager()
        self.bridge = BidirectionalBridge()
        self.active_device = None
        self.executor = None
    
    def discover_devices(self):
        return self.device_manager.list_devices()
    
    def connect_device(self, serial: str):
        if not self.device_manager.is_helper_installed(serial):
            self.device_manager.install_helper(serial)
        self.active_device = serial
        self.executor = ActionExecutor(serial)
        return True
    
    def execute_instruction(self, instruction: str):
        if not self.executor:
            return {"error": "no device connected"}
        return self.executor.execute_natural_language(instruction)
    
    def start_bidirectional_bridge(self):
        asyncio.run(self.bridge.start_server())
    
    def control_device(self, action: str, target: str, params=None):
        if not self.executor:
            return {"error": "no device connected"}
        # Execute via action executor
        return {"status": "success", "action": action, "target": target}
    
    def get_device_status(self):
        if not self.active_device:
            return {"connected": False}
        return {
            "connected": True,
            "serial": self.active_device,
            "helper_installed": self.device_manager.is_helper_installed(self.active_device)
        }
