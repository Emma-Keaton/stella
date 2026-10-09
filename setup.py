import subprocess
import sys
import time
import urllib.request

def check_network_speed():
    print("Checking network speed...")
    test_url = "https://pypi.org/simple/"
    try:
        start = time.time()
        req = urllib.request.Request(test_url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = time.time() - start
            if elapsed > 3:
                print(f"  [WARNING] Slow network detected ({elapsed:.1f}s latency). Large downloads may take longer.")
            else:
                print(f"  Network OK ({elapsed:.2f}s latency)")
    except Exception as e:
        print(f"  [WARNING] Could not check network: {e}")

def install_package(pkg):
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  [OK] {pkg}")
        return True
    else:
        err = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "unknown error"
        print(f"  [FAIL] {pkg}: {err}")
        return False

check_network_speed()

print("\nInstalling requirements...")
with open("requirements.txt") as f:
    packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

failed = []
for pkg in packages:
    if not install_package(pkg):
        failed.append(pkg)

print("\nInstalling Playwright browsers...")
result = subprocess.run([sys.executable, "-m", "playwright", "install"], capture_output=True, text=True)
if result.returncode == 0:
    print("  [OK] Playwright browsers")
else:
    print(f"  [FAIL] Playwright: {result.stderr.strip().split(chr(10))[-1]}")
    failed.append("playwright")

print("\nDownloading Piper TTS voice models...")
import pathlib
voice_dir = pathlib.Path(__file__).resolve().parent / ".venv" / "piper" / "voices"
voice_dir.mkdir(parents=True, exist_ok=True)

voices = {
    "en_US-lessac-medium": ("en_US-lessac-medium.onnx", "en_US-lessac-medium.onnx.json"),
    "en_US-amy-medium": ("en_US-amy-medium.onnx", "en_US-amy-medium.onnx.json"),
    "en_US-kathleen-low": ("en_US-kathleen-low.onnx", "en_US-kathleen-low.onnx.json"),
}

base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
for name, (onnx, cfg) in voices.items():
    if (voice_dir / onnx).exists():
        print(f"  [SKIP] {name} already exists")
        continue
    lang = name.split("-")[0].replace("en_", "en/")
    quality = name.split("-")[-1] if "-" in name else "medium"
    try:
        import urllib.request
        url_onnx = f"{base_url}/{lang}/{onnx}"
        url_cfg = f"{base_url}/{lang}/{cfg}"
        print(f"  Downloading {name}...")
        urllib.request.urlretrieve(url_onnx, str(voice_dir / onnx))
        urllib.request.urlretrieve(url_cfg, str(voice_dir / cfg))
        print(f"  [OK] {name}")
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed.append(name)

print("\n" + "=" * 50)
if failed:
    print(f"Setup completed with {len(failed)} failure(s):")
    for f in failed:
        print(f"  - {f}")
    print("\nSome packages failed to install. Check messages above for details.")
else:
    print("Setup complete! Run 'python main.py' or start_brahma.bat to start Stella.")
