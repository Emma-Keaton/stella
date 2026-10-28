with open(r'E:\Projects\stella\ui.py', 'rb') as f:
    content = f.read()
old = b'return False, f"Error pinning to taskbar: {e}"\r\n\r\nclass SmartDevicesSection(QFrame):'
new = b'return False, f"Error pinning to taskbar: {e}"\r\n\r\n    def _on_vault_enabled_toggled(self, enabled: bool):\r\n        settings = self._load_app_settings()\r\n        settings["memory_vault_enabled"] = bool(enabled)\r\n        self._save_app_settings(settings)\r\n        if hasattr(self, "_vault_folder_input"):\r\n            self._vault_folder_input.setEnabled(enabled)\r\n        if hasattr(self, "_vault_folder_btn"):\r\n            self._vault_folder_btn.setEnabled(enabled)\r\n\r\n    def _pick_vault_folder(self):\r\n        from PyQt6.QtWidgets import QFileDialog\r\n        from pathlib import Path\r\n        folder = QFileDialog.getExistingDirectory(self, "Select Memory Vault Folder", self._vault_folder_input.text() or str(Path.home()))\r\n        if folder:\r\n            self._vault_folder_input.setText(folder)\r\n            settings = self._load_app_settings()\r\n            settings["memory_vault_folder"] = folder\r\n            self._save_app_settings(settings)\r\n\r\nclass SmartDevicesSection(QFrame):'
content = content.replace(old, new)
with open(r'E:\Projects\stella\ui.py', 'wb') as f:
    f.write(content)
print('Added handler methods')