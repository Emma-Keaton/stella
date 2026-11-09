# Skill: smart_home_service

Smart home service layer for managing providers, accounts, and devices.

## Components

- **ProviderRegistry** - Registry for loading and managing providers
- **SmartHomeService** - Main service for device management
- **PlatformInfo** - Platform information data class

## Usage

```python
from skills.smart_home_service import SmartHomeService, ProviderRegistry

service = SmartHomeService()
platforms = service.list_platforms()
# Returns list of available platforms
```

## Methods

- `list_platforms()` - List all available platforms
- `auth_fields_for(provider_key)` - Get auth fields for a provider
- `preview_discovery(provider_key, credentials)` - Preview device discovery
- `connect_devices(provider_key, account_label, credentials, external_ids)` - Connect devices
- `get_devices()` - List all connected devices
- `execute_device(device_id, action, payload)` - Execute action on device
- `remove_device(device_id)` - Remove a device
- `parse_command(text)` - Parse natural language command
- `route_command(text)` - Route command to device