"""
Artemis Device Manager for Stella
Handles ADB device discovery, helper installation, and connection management
"""

import subprocess
import time
from typing import List, Dict, Optional

class ArtemisDeviceManager:
    def __init__(self):
        self.devices = []
        self.helper_apk = "artifacts/artemis_helper.apk"
    
    def list_devices(self) -> List[Dict]:
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
        devices = []
        for line in result.stdout.splitlines()[1:]:
            if "device" in line:
                parts = line.split()
                devices.append({
                    "serial": parts[0],
                    "model": self._get_device_model(parts[0]),
                    "connected": True
                })
        self.devices = devices
        return devices
    
    def _get_device_model(self, serial: str) -> str:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "getprop", "ro.product.model"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    
    def install_helper(self, serial: str) -> bool:
        try:
            subprocess.run(
                ["adb", "-s", serial, "install", "-r", self.helper_apk],
                check=True, capture_output=True
            )
            return self._enable_accessibility_helper(serial)
        except Exception as e:
            return False
    
    def _enable_accessibility_helper(self, serial: str) -> bool:
        # Enable accessibility service via ADB settings
        cmd = f"settings put secure enabled_accessibility_services com.google.artemis.helper/.ArtemisService"
        subprocess.run(["adb", "-s", serial, "shell", cmd], check=True)
        return True
    
    def is_helper_installed(self, serial: str) -> bool:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "pm", "list", "packages", "com.google.artemis.helper"],
            capture_output=True, text=True
        )
        return "com.google.artemis.helper" in result.stdout
