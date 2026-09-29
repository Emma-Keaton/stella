import os
import sys
import subprocess
import threading
import time
import requests
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

GITHUB_REPO = "titechprabhasolutions/Brahma---personal"

def get_current_version() -> str:
    try:
        if hasattr(sys, '_MEIPASS'):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).resolve().parent.parent
            
        version_file = base_dir / "app_version.txt"
        if version_file.exists():
            return version_file.read_text(encoding='utf-8').strip()
    except Exception:
        pass
    return "1.0.0"

def parse_semver(ver: str) -> tuple:
    if ver.startswith('v'):
        ver = ver[1:]
    parts = ver.split('.')
    return tuple(int(x) if x.isdigit() else 0 for x in parts)

# Global holder for the latest OTA release data so apply_update_and_restart can access it
_LATEST_OTA_RELEASE = None

class UpdateChecker(QObject):
    update_available_sig = pyqtSignal(str)

    def __init__(self, repo_owner="titechprabhasolutions", repo_name="Brahma---personal", branch="main"):
        super().__init__()
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self._stop_event = threading.Event()
        self._check_thread = None

    def start(self):
        if self._check_thread is None:
            self._check_thread = threading.Thread(target=self._check_loop, daemon=True, name="updater-thread")
            self._check_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._check_thread:
            self._check_thread.join(timeout=1.0)

    def _get_ota_release(self):
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('tag_name', '')
                if not latest_version:
                    return None
                    
                current = parse_semver(get_current_version())
                latest = parse_semver(latest_version)
                
                if latest > current:
                    assets = data.get('assets', [])
                    setup_asset = next((a for a in assets if 'setup' in a.get('name', '').lower() or 'installer' in a.get('name', '').lower()), None)
                    if not setup_asset:
                        setup_asset = next((a for a in assets if a.get('name', '').endswith('.exe')), None)
                        
                    if setup_asset:
                        return {
                            'version': latest_version,
                            'url': setup_asset.get('browser_download_url'),
                            'size': setup_asset.get('size', 0)
                        }
        except Exception as e:
            print(f"[Updater] Error fetching remote release: {e}")
        return None

    def _check_loop(self):
        global _LATEST_OTA_RELEASE
        while not self._stop_event.is_set():
            # If running from source (has .git), fallback to git updater logic could go here, 
            # but we'll assume we want the OTA for the .exe
            is_compiled = hasattr(sys, '_MEIPASS')
            
            if is_compiled:
                release_data = self._get_ota_release()
                if release_data:
                    _LATEST_OTA_RELEASE = release_data
                    print(f"[Updater] Update detected! Local: {get_current_version()}, Remote: {release_data['version']}")
                    self.update_available_sig.emit(release_data['version'])
                    break
            else:
                # If running from source, skip OTA loop
                break

            for _ in range(3600):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

def apply_update_and_restart():
    global _LATEST_OTA_RELEASE
    is_compiled = hasattr(sys, '_MEIPASS')
    
    if not is_compiled:
        print("[Updater] Not running as a compiled exe. Skipping OTA apply.")
        return

    if not _LATEST_OTA_RELEASE:
        print("[Updater] No OTA release data found.")
        return
        
    print(f"[Updater] Downloading update from {_LATEST_OTA_RELEASE['url']} ...")
    try:
        from core.user_paths import get_user_data_dir
        update_dir = get_user_data_dir() / "updates"
        update_dir.mkdir(parents=True, exist_ok=True)
        setup_path = update_dir / "BrahmaEcho_Setup_Update.exe"
        
        response = requests.get(_LATEST_OTA_RELEASE['url'], stream=True, timeout=15)
        response.raise_for_status()
        
        with open(setup_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        if setup_path.exists():
            print(f"[Updater] Launching silent updater: {setup_path}")
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen([str(setup_path), "--silent"], creationflags=subprocess.CREATE_NO_WINDOW | DETACHED_PROCESS)
            sys.exit(0)
            
    except Exception as e:
        print(f"[Updater] Failed to download or apply update: {e}")
