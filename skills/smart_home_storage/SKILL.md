# Skill: smart_home_storage

Smart home storage layer for encrypted credential storage and device management.

## Components

- **CredentialVault** - Encrypted credential storage using Fernet
- **SmartHomeStorage** - SQLite-based storage for devices and accounts

## Usage

```python
from skills.smart_home_storage import SmartHomeStorage, CredentialVault

storage = SmartHomeStorage()
vault = CredentialVault()

# Store credentials
encrypted = vault.encrypt_json({"token": "secret"})
# Retrieve credentials
decrypted = vault.decrypt_json(encrypted)
```

## Storage Methods

- `add_provider_account(provider_key, account_label, credentials)` - Add provider account
- `list_provider_accounts()` - List all accounts
- `get_provider_account(account_id)` - Get specific account
- `remove_provider_account(account_id)` - Remove account
- `add_device(...)` - Add device
- `list_devices()` - List all devices
- `get_device(device_id)` - Get specific device
- `update_device(device_id, ...)` - Update device
- `forget_device(device_id)` - Remove device
- `log_activity(title, detail)` - Log activity
- `recent_activity(limit)` - Get recent activities
- `count_devices()` - Count total devices

## Encryption

Uses Fernet symmetric encryption for credential storage.