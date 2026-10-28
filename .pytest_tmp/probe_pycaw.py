from ctypes import POINTER, cast

from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

devices = AudioUtilities.GetSpeakers()
print("GetSpeakers:", devices)
print("type:", type(devices))

volume = cast(devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None),
              POINTER(IAudioEndpointVolume))
print("volume:", volume)
print("level:", volume.GetMasterVolumeLevelScalar())

all_devs = AudioUtilities.GetAllDevices()
print("all devices:", len(all_devs))
for device in all_devs[:5]:
    try:
        store = device.OpenPropertyStore(0)
        name = store.GetValue("{a45c254e-df1c-4efd-8020-67d146a850e0}").GetValue()
    except Exception as exc:
        name = f"? ({type(exc).__name__}: {exc})"
    print("  -", device, name)
