# Skill: smart_device_manager

Singleton device manager for tracking active device context and routing commands.

## Components

- **SmartDeviceManager** - Singleton manager for active device context

## Usage

```python
from skills.smart_device_manager import SmartDeviceManager

manager = SmartDeviceManager()
manager.set_active_device("device_id", "Living Room Fan")
# Later commands like "turn on" will be routed to "Living Room Fan"
```

## Methods

- `set_active_device(device_id, device_name)` - Set active device
- `get_active_device_id()` - Get active device ID
- `get_active_device_name()` - Get active device name
- `route_command(text, devices)` - Route command to active device if generic

## Usage

The manager automatically routes generic commands (like "turn on") to the active device when no specific device is mentioned.