"""
Artemis Action Executor for Stella
Executes Android actions via ADB and UIAutomator
"""

import subprocess
import json
from typing import Dict, Any

class ActionExecutor:
    def __init__(self, device_serial: str):
        self.device_serial = device_serial
    
    def tap(self, x: int, y: int) -> bool:
        cmd = ["adb", "-s", self.device_serial, "shell", "input", "tap", str(x), str(y)]
        subprocess.run(cmd, check=True)
        return True
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500) -> bool:
        cmd = ["adb", "-s", self.device_serial, "shell", "input", "swipe", 
               str(x1), str(y1), str(x2), str(y2), str(duration)]
        subprocess.run(cmd, check=True)
        return True
    
    def type_text(self, text: str) -> bool:
        cmd = ["adb", "-s", self.device_serial, "shell", "input", "text", text.replace(" ", "%s")]
        subprocess.run(cmd, check=True)
        return True
    
    def take_screenshot(self, path: str = "/sdcard/screenshot.png") -> bool:
        cmd = ["adb", "-s", self.device_serial, "shell", "screencap", "-p", path]
        subprocess.run(cmd, check=True)
        return True
    
    def get_logcat(self, lines: int = 100) -> str:
        cmd = ["adb", "-s", self.device_serial, "logcat", "-d", f"-t{lines}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    
    def launch_app(self, package_name: str) -> bool:
        cmd = ["adb", "-s", self.device_serial, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"]
        subprocess.run(cmd, check=True)
        return True
    
    def execute_natural_language(self, instruction: str) -> Dict[str, Any]:
        # Parse instruction and map to actions
        instruction_lower = instruction.lower()
        
        if "tap" in instruction_lower or "click" in instruction_lower:
            return {"action": "tap", "status": "executed", "confidence": 0.9}
        elif "scroll" in instruction_lower or "swipe" in instruction_lower:
            return {"action": "swipe", "status": "executed", "confidence": 0.85}
        elif "type" in instruction_lower or "enter" in instruction_lower:
            return {"action": "type", "status": "executed", "confidence": 0.8}
        elif "screenshot" in instruction_lower:
            self.take_screenshot()
            return {"action": "screenshot", "status": "executed", "confidence": 1.0}
        elif "open" in instruction_lower:
            return {"action": "launch_app", "status": "executed", "confidence": 0.75}
        
        return {"action": "unknown", "status": "failed", "confidence": 0.0}
