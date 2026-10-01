"""
Interactive Sensorium Test Harness (v2)
Runs a real-time terminal monitor that shows how Brahma passively observes your actions
and triggers autonomous interjections without you saying or prompting a single word.
"""

import time
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.sensorium import sensorium

print("=" * 65)
print("  BRAHMA EVO v2: PASSIVE SENSORIUM LIVE TEST")
print("=" * 65)
print("Instructions:")
print("1. Switch between different windows (Browser, Explorer, Terminal, etc.)")
print("2. Leave your mouse and keyboard alone for 10 seconds to test 'Away' detection.")
print("3. Notice how it tracks your focus without you asking anything.")
print("Press Ctrl+C to stop.\n")

last_window = ""
idle_alerted = False

def speak_proactive(text):
    try:
        import win32com.client
        import threading
        def _speak():
            try:
                voice = win32com.client.Dispatch("SAPI.SpVoice")
                voice.Speak(text)
            except Exception:
                pass
        threading.Thread(target=_speak, daemon=True).start()
    except Exception:
        pass

def on_interjection(alert_type, meta):
    msg = meta.get("message", "")
    speech = meta.get("speech", msg)
    print(f"\n⚡ [AUTONOMOUS INTERJECTION - {alert_type.upper()}]: {msg}")
    print(f"🔊 [BRAHMA SPEAKING]: \"{speech}\"\n")
    speak_proactive(speech)

sensorium.register_interjection_handler(on_interjection)
sensorium.start()

try:
    streak = 0
    while True:
        snap = sensorium.get_snapshot()
        current_win = snap["window_title"]
        proc = snap["process_name"]
        dwell = snap["dwell_seconds"]
        idle = snap["user_idle_seconds"]
        ram = snap["ram_percent"]

        # Check for window switch
        if current_win and current_win != last_window:
            print(f"👁️  [FOCUS SWITCH] App: {proc} | Window: {current_win[:40]}...")
            last_window = current_win
            idle_alerted = False
            streak = 0

        # Autonomous Trigger: Stepped away for > 10 seconds
        if idle >= 10.0 and not idle_alerted:
            print(f"\n💤 [SENSORIUM TRIGGER]: Hands off controls for {idle:.0f}s. User marked as AWAY.")
            idle_alerted = True

        if idle < 2.0 and idle_alerted:
            msg = f"Welcome back, sir. Your workspace on {proc} is ready."
            print(f"\n✨ [SENSORIUM TRIGGER]: {msg}")
            print(f"🔊 [BRAHMA SPEAKING]: \"{msg}\"\n")
            speak_proactive(msg)
            idle_alerted = False

        # Autonomous Trigger: Short 15s focus streak demo
        if dwell >= 15.0 and streak == 0 and idle < 3.0:
            msg = f"Deep focus streak on {proc} detected. Running smooth."
            print(f"\n🎯 [SENSORIUM TRIGGER]: {msg}")
            print(f"🔊 [BRAHMA SPEAKING]: \"{msg}\"\n")
            speak_proactive(msg)
            streak = 1

        time.sleep(1.0)

except KeyboardInterrupt:
    sensorium.stop()
    print("\nSensorium stopped.")
