from ctypes import POINTER, cast

from comtypes import CLSCTX_ALL, CoInitialize
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

CoInitialize()
speakers = AudioUtilities.GetSpeakers()
print("wrapper:", speakers)
print("endpoint attr:", speakers.endpoint)
endpoint = speakers.endpoint
volume = cast(endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None),
              POINTER(IAudioEndpointVolume))
print("volume:", volume)
print("level:", volume.GetMasterVolumeLevelScalar())
print("mute:", volume.GetMute())

# device names
count = len(AudioUtilities.GetAllDevices())
print("devices:", count)
for device in AudioUtilities.GetAllDevices():
    try:
        store = device.OpenPropertyStore(0)
        value = store.GetValue("{a45c254e-df1c-4efd-8020-67d146a850e0}")
        print("  raw value:", repr(value), "GetValue:", value.GetValue())
    except Exception as exc:
        print("  err", type(exc).__name__, exc)
