#!/data/data/com.termux/files/usr/bin/bash
# grant_stella_permissions.sh - grant Stella's runtime permissions over ADB,
# from the phone itself (Termux).
#
# Why this exists: Android gives no app the ability to grant its own dangerous
# permissions. `pm grant` works from the shell/ADB user, which Termux can
# reach over wireless debugging - so you can do this without a PC and without
# rooting.
#
# The app also has a one-tap "Grant all" button, so this is optional.
#
# Setup (one time):
#   1. Settings > Developer options > Wireless debugging ON
#   2. termux-api setup-dialogue  (or pair via the shown code)
#   3. adb pair <ip:port> <code>
#   4. adb connect <ip:port>
#
# Usage:
#   ./grant_stella_permissions.sh                 # public build
#   ./grant_stella_permissions.sh com.stella.connect.k2
#   ./grant_stella_permissions.sh com.stella.connect --revoke

set -uo pipefail

PKG="${1:-com.stella.connect}"
ACTION="${2:-grant}"

# Runtime permissions, newest API first; unknown ones are skipped automatically.
PERMS=(
  android.permission.CAMERA
  android.permission.RECORD_AUDIO
  android.permission.POST_NOTIFICATIONS
  android.permission.ACCESS_COARSE_LOCATION
  android.permission.ACCESS_FINE_LOCATION
  android.permission.ACCESS_BACKGROUND_LOCATION
  android.permission.READ_MEDIA_IMAGES
  android.permission.READ_MEDIA_VIDEO
  android.permission.READ_MEDIA_AUDIO
  android.permission.READ_EXTERNAL_STORAGE
  android.permission.WRITE_EXTERNAL_STORAGE
  android.permission.BLUETOOTH_CONNECT
  android.permission.BLUETOOTH_SCAN
)

if ! command -v adb >/dev/null 2>&1; then
  echo "adb not found in Termux." >&2
  echo "Install it:  pkg install android-tools" >&2
  exit 1
fi

if [ -z "$(adb devices | sed '1d' | grep -w device)" ]; then
  echo "No ADB device connected." >&2
  echo "Enable Wireless debugging, then:" >&2
  echo "  adb pair <ip:port> <code>" >&2
  echo "  adb connect <ip:port>" >&2
  exit 1
fi

if ! adb shell pm list packages "$PKG" | grep -q "$PKG"; then
  echo "Package '$PKG' is not installed." >&2
  exit 1
fi

API=$(adb shell getprop ro.build.version.sdk | tr -d '\r')
echo "device API level: $API"
echo "target: $PKG"
echo

ok=0; skip=0; fail=()
for p in "${PERMS[@]}"; do
  # Skip anything this Android version does not know about.
  if ! adb shell pm list permissions -g 2>/dev/null | grep -q "$p"; then
    skip=$((skip+1)); continue
  fi
  if [ "$ACTION" = "--revoke" ]; then
    if adb shell pm revoke "$PKG" "$p" >/dev/null 2>&1; then
      echo "  revoked ${p##*.}"
    fi
  else
    if adb shell pm grant "$PKG" "$p" >/dev/null 2>&1; then
      echo "  granted ${p##*.}"; ok=$((ok+1))
    else
      fail+=("$p")
    fi
  fi
done

echo
echo "-----------------------------------------"
if [ "$ACTION" = "--revoke" ]; then
  echo "Runtime permissions revoked."
else
  echo "Granted: $ok"
  [ "$skip" -gt 0 ] && echo "Skipped (not on this Android version): $skip"
  if [ ${#fail[@]} -gt 0 ]; then
    echo "Could not grant:"; printf '  %s\n' "${fail[@]}"
  fi
fi

cat <<'NOTE'

Three permissions cannot be granted by any tool - Android needs a human tap:

  1. All files access  : Settings > Apps > Stella > Permissions
                         > Files and media > All the time
  2. Display over apps : Settings > Apps > Stella > Display over other apps
  3. Autopilot         : Settings > Accessibility > Stella Autopilot

Screen control is requested in-app each time it is used, by design.
NOTE