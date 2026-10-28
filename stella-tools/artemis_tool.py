import subprocess
import os
import json
from pathlib import Path

ARTEMIS_ROOT = Path(r"E:\Projects\artemis")
STELLA_DEVICE_SERIAL = None

class ArtemisTool:
    def start_artemis(self):
        if not ARTEMIS_ROOT.exists():
            raise RuntimeError("Artemis not found")
        # Start Artemis server
        cmd = ["uv", "run", "artemis", "ui"]
        proc = subprocess.Popen(cmd, cwd=str(ARTEMIS_ROOT))
        return proc
    
    def install_helper(self, device_serial=None):
        cmd = ["uv", "run", "artemis", "helper", "install"]
        if device_serial:
            cmd.extend(["--serial", device_serial])
        subprocess.run(cmd, cwd=str(ARTEMIS_ROOT), check=True)
    
    def run_task(self, natural_language, device_serial=None, profile="flash"):
        cmd = ["uv", "run", "artemis", "run", natural_language, "--profile", profile]
        if device_serial:
            cmd.extend(["--serial", device_serial])
        result = subprocess.run(cmd, cwd=str(ARTEMIS_ROOT), capture_output=True, text=True)
        return json.loads(result.stdout)
    
    def device_control(self, action, target, params=None):
        # Translate Stella device control into Artemis natural language
        nl = f"{action} {target}"
        if params:
            nl += " with " + ", ".join(f"{k}={v}" for k,v in params.items())
        return self.run_task(nl)
