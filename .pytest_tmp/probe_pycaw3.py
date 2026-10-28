from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

speakers = AudioUtilities.GetSpeakers()
print("attrs:", [name for name in dir(speakers) if not name.startswith("_")])
