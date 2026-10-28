"""
Stella Artemis Controller
Self-contained Android automation for Stella.
Implements natural-language to Android actions without external dependencies.
"""

import subprocess
import json
from typing import Dict, Any, Optional

class ArtemisController:
    def __init__(self, device_serial: Optional[str] = None):
        self.device_serial = device_serial
        self.helper_installed = False
    
    def check_device(self) -> bool:
        cmd = ["adb", "devices"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self.device_serial in result.stdout
    
    def install_helper(self):
        # Install Artemis Accessibility Helper APK
        # In self-contained mode, helper APK is bundled in stella/artifacts/
        apk_path = "artifacts/artemis_helper.apk"
        cmd = ["adb", "install", "-r", apk_path]
        if self.device_serial:
            cmd.insert(1, "-s")
            cmd.insert(2, self.device_serial)
        subprocess.run(cmd, check=True)
        self.helper_installed = True
    
    def execute_natural_language(self, instruction: str, profile: str = "flash") -> Dict[str, Any]:
        # Convert natural language to ADB actions
        # Simplified implementation
        action = self._parse_instruction(instruction)
        result = self._execute_action(action)
        return {
            "success": result,
            "instruction": instruction,
            "action": action,
            "profile": profile
        }
    
    def _parse_instruction(self, instruction: str) -> Dict[str, Any]:
        # Simple parser for demo
        instruction = instruction.lower()
        if "tap" in instruction:
            return {"type": "tap", "target": "screen"}
        elif "screenshot" in instruction:
            return {"type": "screenshot"}
        elif "logcat" in instruction:
            return {"type": "logcat"}
        return {"type": "unknown"}
    
    def _execute_action(self, action: Dict[str, Any]) -> bool:
        try:
            if action["type"] == "tap":
                subprocess.run(["adb", "shell", "input", "tap", "500", "500"], check=True)
            elif action["type"] == "screenshot":
                subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screenshot.png"], check=True)
            elif action["type"] == "logcat":
                subprocess.run(["adb", "logcat", "-d"], check=True)
            return True
        except Exception:
            return False

def get_artemis_controller(device_serial=None):
    return ArtemisController(device_serial)
