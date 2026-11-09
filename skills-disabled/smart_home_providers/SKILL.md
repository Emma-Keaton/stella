# Skill: smart_home_providers

Smart home device providers for integrating with various smart home platforms.

## Providers

### Base Provider
- `SmartHomeProvider` - Abstract base class for all providers
- `ProviderField` - Configuration field definition

### Built-in Providers
- **AtombergProvider** - Atomberg Cloud (fans, ACs)
- **KasaProvider** - TP-Link Kasa (plugs, bulbs, switches)
- **HueProvider** - Philips Hue (lights, sensors)
- **LgProvider** - LG ThinQ (ACs, appliances)
- **DaikinProvider** - Daikin One+ (ACs)
- **TuyaProvider** - Tuya Cloud (plugs, switches, bulbs, ACs, sensors)
- **NestProvider** - Google Nest (thermostats, cameras)
- **SmartThingsProvider** - Samsung SmartThings (sensors, switches)

## Usage

```python
from skills.smart_home_providers.builtin import built_in_provider_classes

providers = built_in_provider_classes()
# Returns list of provider classes
```

## Provider Interface

Each provider implements:
- `auth_fields()` - Required authentication fields
- `authenticate(credentials)` - Authenticate and return credentials
- `discover_devices(credentials)` - Discover devices
- `execute(device, action, payload)` - Execute action on device
- `get_status(device)` - Get device status